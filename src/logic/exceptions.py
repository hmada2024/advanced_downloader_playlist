# src/exceptions.py
# -- ملف لتعريف الاستثناءات (الأخطاء) المخصصة للتطبيق --
# Purpose: Defines custom exceptions used across the application.


class DownloadCancelled(Exception):
    """
    استثناء مخصص يُطلق عندما يقوم المستخدم بإلغاء عملية التحميل أو جلب المعلومات.
    Custom exception raised when the user cancels a download or info fetch operation.
    """

    def __init__(self, message: str = "Operation cancelled by user."):
        """
        Initializes the DownloadCancelled exception.
        Args:
            message (str): The cancellation message.
        """
        super().__init__(message)


# يمكنك إضافة استثناءات أخرى هنا إذا احتجت لاحقًا
# You can add other custom exceptions here if needed later.
