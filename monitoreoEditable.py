import os
import sys
import clr
import pyodbc
import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from dotenv import load_dotenv

# --- CONFIGURACIÓN DE ENTORNO Y RUTAS ---
dir_ejecucion = os.path.dirname(sys.executable if getattr(sys, 'frozen', False) else os.path.abspath(__file__))
load_dotenv(os.path.join(dir_ejecucion, ".env"))

# --- CARGA DE DLL PROCAPS ---
try:
    ruta_dlls = os.path.join(dir_ejecucion, "Librerias")
    sys.path.append(ruta_dlls)
    clr.AddReference("Procaps")
    from Procaps import Utilidades
except Exception as e:
    print(f"Error cargando DLL Procaps: {e}")
    sys.exit(1)


def enviar_correo_html(descripcion, horas_limite, horas_inactivo, ultima_fecha, destino, copia):
    """Genera y envía el correo usando la Descripción en lugar del nombre técnico."""
    try:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = f"ALERTA DE MONITOREO: {descripcion}"
        msg['From'] = os.getenv('EMAIL_USER')
        msg['To'] = destino

        destinatarios = [destino]
        if copia and copia.strip():
            msg['Cc'] = copia
            destinatarios.append(copia)

        html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #2c2c2c; padding: 20px; margin: 0;">
            <div style="max-width: 600px; margin: auto; background-color: #333333; border-radius: 4px; overflow: hidden;">
                <div style="background-color: #006b76; color: #ffffff; padding: 30px; text-align: center;">
                    <h1 style="margin: 0; font-size: 28px; font-weight: bold;">Reporte de Monitoreo</h1>
                    <p style="margin: 5px 0 0 0; font-size: 16px;">Auditoría Automática</p>
                </div>
                <div style="padding: 40px; color: #ffffff;">
                    <h2 style="color: #f27474; border-bottom: 1px solid #444; padding-bottom: 10px; font-size: 20px;">Anomalía Detectada</h2>
                    <p style="font-size: 15px; line-height: 1.6;">El sistema ha detectado que la siguiente tabla ha superado el tiempo de inactividad permitido:</p>

                    <table style="width: 100%; margin-top: 20px; font-size: 15px;">
                        <tr>
                            <td style="padding: 10px 0; color: #00bcd4; font-weight: bold; width: 150px;">Tabla:</td>
                            <td style="padding: 10px 0;">{descripcion}</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #00bcd4; font-weight: bold;">Límite Permitido:</td>
                            <td style="padding: 10px 0;">{horas_limite} hrs</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #f27474; font-weight: bold;">Tiempo Inactivo:</td>
                            <td style="padding: 10px 0; color: #f27474; font-weight: bold;">{horas_inactivo:.2f} hrs</td>
                        </tr>
                        <tr>
                            <td style="padding: 10px 0; color: #00bcd4; font-weight: bold;">Último Registro:</td>
                            <td style="padding: 10px 0;">{ultima_fecha}</td>
                        </tr>
                    </table>

                    <div style="margin-top: 35px; background-color: #4d4d33; border-left: 4px solid #b3b300; padding: 15px; font-size: 14px; line-height: 1.5;">
                        <span style="color: #ffff80; font-weight: bold;">Acción recomendada:</span> Verifique los Jobs de integración o la conectividad del servidor afectado.
                    </div>
                </div>
                <div style="background-color: #262626; color: #888888; padding: 15px; text-align: center; font-size: 12px;">
                    Este es un mensaje automático generado por el sistema de auditoría PYDSTI.
                </div>
            </div>
        </body>
        </html>
        """

        msg.attach(MIMEText(html, 'html'))

        with smtplib.SMTP(os.getenv('SMTP_SERVER'), int(os.getenv('SMTP_PORT')), timeout=15) as server:
            server.sendmail(msg['From'], destinatarios, msg.as_string())

        return True
    except Exception as e:
        print(f"Error enviando correo: {e}")
        return False


def ejecutar_monitoreo():
    status_health = "OK"
    detalles_health = "Ciclo ejecutado correctamente."

    try:
        servidor_config = os.getenv('DB_SERVER')
        pass_config = Utilidades.desEncriptado(os.getenv('DB_PASS_ENC'))

        conn_config_str = (f"DRIVER={{SQL Server}};SERVER={servidor_config};DATABASE={os.getenv('DB_NAME')};"
                           f"UID={os.getenv('DB_USER')};PWD={pass_config};")

        with pyodbc.connect(conn_config_str, timeout=15) as conn_master:
            cursor = conn_master.cursor()
            
            # Consultamos incluyendo la columna de control de ráfagas
            cursor.execute("""
                SELECT servidor_ip, base_datos, tabla_a_monitorear, horas_limite, 
                       correo_destino, correo_copia, columna_fecha, 
                       usuario_db, pass_encriptada_db, descripcion, fecha_ultima_alerta, id
                FROM dbo.mon_config_monitoreo WHERE activo = 1
            """)
            tareas = cursor.fetchall()

            for t in tareas:
                servidor, db, tabla, limite, email_to, email_cc, col_fecha, user_dest, pass_dest_enc, descripcion, f_ultima, id_reg = t
                pass_dest = Utilidades.desEncriptado(pass_dest_enc)
                cadena_conexion_dest = (f"DRIVER={{SQL Server}};SERVER={servidor};DATABASE={db};"
                                        f"UID={user_dest};PWD={pass_dest};")

                try:
                    with pyodbc.connect(cadena_conexion_dest, timeout=10) as conn_dest:
                        c_dest = conn_dest.cursor()
                        c_dest.execute(f"SELECT MAX({col_fecha}) FROM {tabla}")
                        resultado = c_dest.fetchone()[0]

                        if resultado:
                            ultima_f = resultado if isinstance(resultado, datetime) else datetime.strptime(
                                str(resultado)[:19], '%Y-%m-%d %H:%M:%S')

                            fecha_formateada = ultima_f.strftime('%Y-%m-%d %H:%M:%S')
                            dif_horas = (datetime.now() - ultima_f).total_seconds() / 3600

                            if dif_horas >= float(limite):
                                # --- CONTROL DE RÁFAGAS POR HORA ---
                                permitir_envio = False
                                if f_ultima is None:
                                    permitir_envio = True
                                else:
                                    minutos_desde_correo = (datetime.now() - f_ultima).total_seconds() / 60
                                    if minutos_desde_correo >= 55:
                                        permitir_envio = True

                                if permitir_envio:
                                    if enviar_correo_html(descripcion, limite, dif_horas, fecha_formateada, email_to, email_cc):
                                        cursor.execute("""
                                            UPDATE dbo.mon_config_monitoreo 
                                            SET fecha_ultima_alerta = GETDATE() 
                                            WHERE id = ?
                                        """, id_reg)

                                        cursor.execute("""
                                            INSERT INTO dbo.mon_monitoreo_historico_alertas 
                                            (tabla_afectada, fecha_alerta, horas_inactividad, correo_enviado_a, estado_solucion)
                                            VALUES (?, GETDATE(), ?, ?, 'Pendiente')
                                        """, tabla, dif_horas, email_to)
                                        conn_master.commit()
                except Exception as e_serv:
                    detalles_health = f"Advertencia: Fallas de conexion en {servidor}"

            # Actualización del Health Check usando la misma conexión abierta
            cursor.execute("""
                UPDATE dbo.mon_monitoreo_health_check 
                SET ultima_ejecucion = GETDATE(), estado = ?, detalles = ?
                WHERE proceso = 'Monitor Tablas Python'
            """, status_health, detalles_health)
            conn_master.commit()

    except Exception as e:
        print(f"Error general en el sistema: {e}")


if __name__ == "__main__":
    ejecutar_monitoreo()