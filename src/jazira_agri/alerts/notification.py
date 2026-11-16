class Notification:
    @staticmethod
    def format_alert(title, message, level="info"):
        icons = {"info": "ℹ️", "warning": "⚠️", "danger": "🚨", "success": "✅"}
        return f"{icons.get(level, 'ℹ️')} 【{title}】\n{message}"
