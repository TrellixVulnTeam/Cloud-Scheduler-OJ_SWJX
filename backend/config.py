"""Configuration file"""

KUBERNETES_CLUSTER_TOKEN = "eyJhbGciOiJSUzI1NiIsImtpZCI6IiJ9.eyJpc3MiOiJrdWJlcm5ldGVzL3NlcnZpY2VhY2NvdW50Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9uYW1lc3BhY2UiOiJkZWZhdWx0Iiwia3ViZXJuZXRlcy5pby9zZXJ2aWNlYWNjb3VudC9zZWNyZXQubmFtZSI6ImRlZmF1bHQtdG9rZW4tNmQ4MnciLCJrdWJlcm5ldGVzLmlvL3NlcnZpY2VhY2NvdW50L3NlcnZpY2UtYWNjb3VudC5uYW1lIjoiZGVmYXVsdCIsImt1YmVybmV0ZXMuaW8vc2VydmljZWFjY291bnQvc2VydmljZS1hY2NvdW50LnVpZCI6IjY1NjNjMTc1LWViNDgtMTFlOS1hYzA2LTUyMGMzOGUyZjVlNSIsInN1YiI6InN5c3RlbTpzZXJ2aWNlYWNjb3VudDpkZWZhdWx0OmRlZmF1bHQifQ.UTS6FqgyHxKFT7nWbxzbi3qXf8Xx6zIYg-TXJItpX_u4lPFQB6DwlgBMA16Xv3uImhDK857vfh_jyulqTlFZQTx47T3CzZ0NMxdTPYV6jPqdgxOXLixFWmfkVzsup7HhcTjXo67crxTu5pXlUqfDHmlub_JRdkLK5eHvEBU7-ArNWS-2iaeF-zifwih7A52qfxt-87PkFO76c3GetJ9b9RPu5mtVyMA7CaQoj2MZybKiTfq1C_mLgXsCHNwRpubJSBLdNMI9E6QDG99zV2asOMxMoNClrCDNfD97a702_2d2P-KU11yvM37rzMvaJptRFHuXtO_2ow6s9byez1XSGw"
KUBERNETES_API_SERVER_URL = "https://152.136.222.117:30000"
KUBERNETES_NAMESPACE = "cloud-scheduler"
DEBUG = True

USER_TOKEN_EXPIRE_TIME = 900  # in seconds

DOCKER_ADDRESS = "https://registry.dropthu.online:30001"
REGISTRY_ADDRESS = "registry.dropthu.online:30443/nginx"

DAEMON_WORKERS = 4
