# EPG Sistema — Gestión de Presupuestos y Planillas

Sistema web para la gestión de programas académicos, presupuestos y planillas de docentes. Desarrollado para la Escuela de Posgrado (EPG), permite controlar ingresos, gastos y generar reportes financieros por programa.

## Funcionalidades

- **Autenticación y roles**: acceso diferenciado para Administrador, Tesorera y Operador
- **Gestión de programas**: registro de programas académicos con control de ingresos y saldo disponible
- **Registro de gastos**: carga manual e importación desde Excel
- **Planillas docentes**: gestión y aprobación de planillas de docentes invitados
- **Presupuestos**: seguimiento del estado financiero por programa (Normal / Crítico / Sobrepasado)
- **Notificaciones automáticas**: alertas en tiempo real cuando un programa entra en estado crítico o sobrepasado
- **Analytics**: dashboard con métricas y gráficas del estado general
- **Backups automáticos**: respaldo diario de la base de datos

## Tecnologías

| Capa | Tecnología |
|------|-----------|
| Backend | Python 3, Flask |
| Base de datos | SQLite + SQLAlchemy |
| Autenticación | Flask-Login |
| Frontend | HTML, CSS, JavaScript, Jinja2 |
| Importación de datos | openpyxl (Excel) |

## Instalación

```bash
# 1. Clonar el repositorio
git clone https://github.com/billylizama/epg-sistema.git
cd epg-sistema

# 2. Crear entorno virtual
python -m venv venv
venv\Scripts\activate      # Windows
# source venv/bin/activate  # Linux/Mac

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Ejecutar la aplicación
python app.py
```

La aplicación estará disponible en `http://localhost:5000`

## Estructura del proyecto

```
epg-sistema/
├── app.py              # Punto de entrada de la aplicación
├── config.py           # Configuración general
├── extensions.py       # Extensiones Flask (db, login_manager)
├── models/             # Modelos de base de datos
│   ├── usuario.py
│   ├── programa.py
│   ├── registro_gasto.py
│   └── notificacion.py
├── routes/             # Blueprints y lógica de rutas
│   ├── auth.py
│   ├── admin.py
│   ├── tesorera.py
│   ├── operador.py
│   └── analytics.py
├── templates/          # Plantillas HTML (Jinja2)
├── static/             # Archivos estáticos (CSS, JS, imágenes)
└── requirements.txt
```

## Autor

**Billy Lizama**
[github.com/billylizama](https://github.com/billylizama)
