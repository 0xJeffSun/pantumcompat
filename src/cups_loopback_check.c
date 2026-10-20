/* SPDX-License-Identifier: AGPL-3.0-or-later */
/* Exercise the genuine CUPS filter sandbox, delivering only to 127.0.0.1. */
#include <cups/cups.h>
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

static int command(char *const argv[]) {
    pid_t p=fork(); if(p<0)return -1;
    if(!p){execv(argv[0],argv);_exit(127);}
    int status=0;while(waitpid(p,&status,0)<0){if(errno!=EINTR)return -1;}
    return WIFEXITED(status)?WEXITSTATUS(status):-1;
}
static ipp_jstate_t job_state(const char *queue,int id) {
    (void)queue;
    ipp_jstate_t state=IPP_JOB_PENDING;
    char uri[128];snprintf(uri,sizeof(uri),"ipp://localhost/jobs/%d",id);
    ipp_t *request=ippNewRequest(IPP_OP_GET_JOB_ATTRIBUTES);
    ippAddString(request,IPP_TAG_OPERATION,IPP_TAG_URI,"job-uri",NULL,uri);
    ippAddString(request,IPP_TAG_OPERATION,IPP_TAG_NAME,"requesting-user-name",NULL,cupsUser());
    ippAddString(request,IPP_TAG_OPERATION,IPP_TAG_KEYWORD,"requested-attributes",NULL,"job-state");
    ipp_t *response=cupsDoRequest(CUPS_HTTP_DEFAULT,request,"/");
    if(response){
        ipp_attribute_t *attr=ippFindAttribute(response,"job-state",IPP_TAG_ENUM);
        if(attr)state=(ipp_jstate_t)ippGetInteger(attr,0);
        ippDelete(response);
    }
    return state;
}
int main(int argc,char **argv){
    if(argc!=4){fprintf(stderr,"Usage: check ppd fixture.pdf captured.prn\n");return 1;}
    int rc=1,fd=-1,conn=-1,out=-1,job=0,created=0;
    char queue[96],uri[160];
    unsigned char buf[65536],head[160]={0},tail[9]={0};size_t head_n=0,total=0;
    snprintf(queue,sizeof(queue),"PantumCompat_SelfCheck_%ld",(long)getpid());
    cupsSetServer("/private/var/run/cupsd");
    signal(SIGPIPE,SIG_IGN);
    fd=socket(AF_INET,SOCK_STREAM,0);if(fd<0)goto done;
    fcntl(fd,F_SETFD,FD_CLOEXEC);
    struct sockaddr_in addr={0};addr.sin_family=AF_INET;addr.sin_addr.s_addr=htonl(INADDR_LOOPBACK);
    if(bind(fd,(struct sockaddr*)&addr,sizeof(addr))||listen(fd,1))goto done;
    socklen_t alen=sizeof(addr);if(getsockname(fd,(struct sockaddr*)&addr,&alen))goto done;
    snprintf(uri,sizeof(uri),"socket://127.0.0.1:%u/?contimeout=10&waiteof=false",ntohs(addr.sin_port));
    char *add[]={"/usr/sbin/lpadmin","-p",queue,"-E","-v",uri,"-P",argv[1],
        "-o","printer-is-shared=false","-o","printer-error-policy=abort-job",NULL};
    if(command(add))goto done;
    created=1;
    cups_option_t *opts=NULL;int n=0;
    n=cupsAddOption("PageSize","A4",n,&opts);
    n=cupsAddOption("sides","one-sided",n,&opts);
    n=cupsAddOption("copies","1",n,&opts);
    job=cupsPrintFile(queue,argv[2],"Pantum local conversion self-check",n,opts);
    cupsFreeOptions(n,opts);
    if(job<=0){fprintf(stderr,"Self-check submission failed: %s\n",cupsLastErrorString());goto done;}
    fprintf(stderr,"Local CUPS self-check: queue=%s job=%d destination=%s\n",queue,job,uri);
    time_t deadline=time(NULL)+75;
    while(time(NULL)<deadline){
        struct pollfd p={.fd=fd,.events=POLLIN};
        int ready=poll(&p,1,500);
        if(ready>0){conn=accept(fd,NULL,NULL);break;}
        if(ready<0&&errno!=EINTR)goto done;
        ipp_jstate_t state=job_state(queue,job);
        if(state==IPP_JOB_ABORTED||state==IPP_JOB_CANCELED||state==IPP_JOB_STOPPED||state==IPP_JOB_HELD){fprintf(stderr,"CUPS job failed or stopped before producing data (state=%d).\n",state);goto done;}
    }
    if(conn<0){fprintf(stderr,"No loopback connection before timeout.\n");goto done;}
    struct timeval limit={.tv_sec=60,.tv_usec=0};setsockopt(conn,SOL_SOCKET,SO_RCVTIMEO,&limit,sizeof(limit));
    out=open(argv[3],O_WRONLY|O_CREAT|O_TRUNC,0600);if(out<0)goto done;
    for(;;){
        ssize_t k=read(conn,buf,sizeof(buf));
        if(k<0&&errno==EINTR)continue;
        if(k<0)goto done;
        if(!k)break;
        if(head_n<sizeof(head)-1){size_t m=(size_t)k;if(m>sizeof(head)-1-head_n)m=sizeof(head)-1-head_n;memcpy(head+head_n,buf,m);head_n+=m;}
        if(k>=9)memcpy(tail,buf+k-9,9);
        else {memmove(tail,tail+k,9-(size_t)k);memcpy(tail+9-k,buf,(size_t)k);}
        total+=(size_t)k;
        ssize_t left=k;unsigned char *p=buf;
        while(left){ssize_t w=write(out,p,(size_t)left);if(w<0&&errno==EINTR)continue;if(w<=0)goto done;p+=w;left-=w;}
    }
    for(size_t i=0;i<head_n;i++)head[i]^=0xa5;
    for(size_t i=0;i<9;i++)tail[i]^=0xa5;
    if(total<1000||head_n<9||memcmp(head,"\033%-12345X",9)||!strstr((char*)head,"PCLXL")||memcmp(tail,"\033%-12345X",9)){
        fprintf(stderr,"Loopback received invalid/incomplete encoded PCL XL (%zu bytes).\n",total);goto done;
    }
    for(int i=0;i<30;i++){
        ipp_jstate_t state=job_state(queue,job);
        if(state==IPP_JOB_COMPLETED){rc=0;break;}
        if(state==IPP_JOB_ABORTED||state==IPP_JOB_CANCELED||state==IPP_JOB_STOPPED||state==IPP_JOB_HELD)break;
        usleep(200000);
    }
    if(!rc)fprintf(stderr,"PASS: genuine CUPS completed job%d and loopback received %zu encoded bytes. No physical printer was contacted.\n",job,total);
done:
    if(out>=0)close(out);if(conn>=0)close(conn);if(fd>=0)close(fd);
    if(created){
        if(rc&&job>0)cupsCancelJob2(CUPS_HTTP_DEFAULT,queue,job,0);
        char *del[]={"/usr/sbin/lpadmin","-x",queue,NULL};command(del);
    }
    if(rc)fprintf(stderr,"FAIL: local CUPS self-check failed; inspect /var/log/cups/error_log for job%d.\n",job);
    return rc;
}
