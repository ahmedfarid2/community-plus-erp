{
    "name": "OneSuite Hub",
    "version": "19.0.1.0.0",
    "category": "Productivity",
    "summary": "NextGen application and service launcher for OneSuite",
    "author": "NextGen Technology PNG Limited",
    "website": "https://nextgenpng.net",
    "license": "LGPL-3",
    "depends": ["base", "web", "community_plus_theme"],
    "data": [
        "security/ir.model.access.csv",
        "data/onesuite_app_data.xml",
        "views/onesuite_app_views.xml",
    ],
    "installable": True,
    "application": True,
}
