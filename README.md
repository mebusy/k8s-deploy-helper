# k8s-deploy-helper

aws EKS, tencent TKE,  deploy helper


1. add submodule
    ```bash
    git submodule add -b deploy-helper https://github.com/mebusy/k8s-deploy-helper.git helper
    ```
2. in `example` folder
    - edit conf.yaml
3. put your local k8s config file to `example/kubeconfs/local.conf`
    - put your remote  k8s config file to `example/kubeconfs/prod.conf`
4. deploy your service to local k8s by executing  `example/deploy_local.sh`

