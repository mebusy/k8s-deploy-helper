

AWS workflow

1. create namespace
2. ecr, image repos
    - config `ecr` root and aws image repos  in `conf.yaml` 
3. create ecr image repository
4. doploy to k8s
    - after deploy ingress successfully , aws will generate a loadbalancer automatically ( **it will consume IP, be careful**. )
5. create domain/parser
    - pointer to the loadbalancer created by AWS
6. upload image & restrat



For Tencent Cloud, you should do extra work

1. in tencent cloud console, go to namespace,  下发镜像仓库秘钥 `qcloudregistrykey`
2. edit ingress yaml to use https 








