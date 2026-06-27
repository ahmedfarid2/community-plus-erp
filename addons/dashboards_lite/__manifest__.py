{
    "name": "Dashboards (Lite)",
    "version": "19.0.1.1.0",
    "category": "Productivity/Dashboards",
    "summary": "Unified company KPI dashboard across all apps",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["account"],
    "data": ["security/ir.model.access.csv", "views/board_views.xml"],
    "assets": {
        "web.assets_backend": [
            "dashboards_lite/static/src/scss/dashboard.scss",
        ],
    },
    "installable": True,
    "application": True,
}
