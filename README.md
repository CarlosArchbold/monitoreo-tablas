# Sistema Automatizado de Monitoreo de Tablas B2B

Este sistema en Python audita la inactividad de bases de datos relacionales distribuidas (SQL Server) para asegurar la continuidad de los flujos de información de integración. 

## 🚀 Características
- **Configuración Dinámica:** Servidores maestros parametrizables a través de variables de entorno `.env`.
- **Arquitectura de Seguridad:** Consumo modular de componentes de desencriptado empresarial para el manejo seguro de credenciales.
- **Evitación de Spam:** Control lógico de alertas por hora (rango de 55-60 min) para mitigar ráfagas duplicadas de correos SMTP en entornos de producción.
- **Health Check Centralizado:** Reporte de estado directo a un dashboard web/base de datos para auditoría en tiempo real.

## 🛠️ Requisitos e Instalación
1. Clonar el repositorio.
2. Instalar las dependencias necesarias:
   ```bash
   pip install -r requirements.txt