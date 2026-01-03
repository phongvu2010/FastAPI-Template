listener "tcp" {
  address     = "0.0.0.0:8200"
  tls_disable = 1 # KHÔNG SỬ DỤNG TRONG PROD THỰC TẾ! Cần bật TLS và chứng chỉ.
}

storage "postgresql" {
  connection_url = "postgresql://${VAULT_DB_USER}:${VAULT_DB_PASSWORD}@${VAULT_DB_HOST}:5432/${VAULT_DB_NAME}?sslmode=disable"
}

ui = true
