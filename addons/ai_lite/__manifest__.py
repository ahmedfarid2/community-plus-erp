{
    "name": "AI Assistant (Lite)",
    "version": "19.0.1.0.0",
    "category": "Productivity/AI",
    "summary": "Chat assistant backed by Ollama (free local) or OpenAI/Anthropic",
    "author": "Farid",
    "license": "LGPL-3",
    "depends": ["base_setup"],
    "data": [
        "security/ir.model.access.csv",
        "views/assistant_views.xml",
        "views/settings_views.xml",
    ],
    "installable": True,
    "application": True,
}
