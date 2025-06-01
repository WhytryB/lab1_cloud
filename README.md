# lab1_cloud
# IoT Monitoring Service

Простий сервіс для моніторингу IoT пристроїв на Google Cloud Platform.

## Запуск локально

1. Встановіть залежності:
```bash
pip install -r requirements.txt

cd terraform
terraform init
terraform apply

kubectl apply -f k8s/