# myapp/middleware.py
from django.conf import settings
from django.http import JsonResponse
import time
import logging
from django.utils.deprecation import MiddlewareMixin
from datetime import datetime

# logger = logging.getLogger(__name__)

# class RequestLoggingMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         request.start_time = time.time()
#         logger.info(f"Request: {request.method} {request.get_full_path()}")
#
#     def process_response(self, request, response):
#         if hasattr(request, 'start_time'):
#             elapsed_time = time.time() - request.start_time
#             logger.info(f"Response: {response.status_code} - Time: {elapsed_time:.2f}s")
#         return response

class FileSizeLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Lấy kích thước tối đa từ settings
        max_total_file_size = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)  # 5MB mặc định

        if request.method in ['POST', 'PATCH'] and request.FILES:
            total_file_size = self.calculate_total_file_size(request)

            if total_file_size > max_total_file_size:
                return JsonResponse(
                    {
                        'detail': f'Total file size exceeds the limit. Maximum allowed total size is {max_total_file_size // (1024 * 1024)}MB.'},
                    status=400
                )

        return None

    def calculate_total_file_size(self, request):
        total_file_size = 0

        # Kiểm tra nếu có các tệp trong 'media'
        if 'media' in request.FILES:
            files = request.FILES.getlist('media')
            if files:
                for file in files:
                    total_file_size += file.size
        else:
            for file in request.FILES.values():
                total_file_size += file.size

        return total_file_size

class FileExtensionWhitelistMiddleware(MiddlewareMixin):
    ALLOWED_EXTENSIONS = ['jpeg', 'pdf', 'ico', 'jpg', 'png']

    def process_request(self, request):
        if request.method in ['POST', 'PATCH'] and request.FILES:
            invalid_file = self.check_file_extensions(request)
            if invalid_file:
                return JsonResponse(
                    {'detail': f"Invalid file extension for {invalid_file}."},
                    status=400
                )
        return None

    def check_file_extensions(self, request):
        # Kiểm tra tệp trong 'media'
        if 'media' in request.FILES:
            files = request.FILES.getlist('media')
            for file in files:
                file_extension = self.get_file_extension(file.name)
                if file_extension not in self.ALLOWED_EXTENSIONS:
                    return file.name

        # Kiểm tra tệp ngoài 'media'
        for file_key, file in request.FILES.items():
            file_extension = self.get_file_extension(file.name)
            if file_extension not in self.ALLOWED_EXTENSIONS:
                return file_key

        return None

    def get_file_extension(self, filename):
        return filename.split('.')[-1].lower()


# class FileValidationMiddleware(MiddlewareMixin):
#     ALLOWED_MIME_TYPES = {
#         'jpg': 'JPEG image data',
#         'jpeg': 'JPEG image data',
#         'png': 'PNG image data',
#         'pdf': 'PDF document',
#         'ico': 'image/x-icon',
#     }
#
#     def process_request(self, request):
#         if request.method in ['POST', 'PATCH'] and request.FILES:
#             invalid_file = self.validate_files(request)
#             if invalid_file:
#                 return JsonResponse(
#                     {'detail': invalid_file},
#                     status=400
#                 )
#         return None
#     """
#     Tạo phương thức validate_files: Phương thức này kiểm tra các tệp trong media và các tệp khác, giúp mã dễ đọc và bảo trì hơn.
#     """
#     def validate_files(self, request):
#         mime = magic.Magic()
#
#         # Kiểm tra tệp trong 'media'
#         if 'media' in request.FILES:
#             files = request.FILES.getlist('media')
#             for file in files:
#                 error_message = self.check_file_mime(file, mime)
#                 if error_message:
#                     return error_message
#
#         # Kiểm tra tệp ngoài 'media'
#         for file_key, file in request.FILES.items():
#             error_message = self.check_file_mime(file, mime)
#             if error_message:
#                 return error_message
#
#         return None
#     """
#     Tạo phương thức check_file_mime: Phương thức này kiểm tra MIME type của tệp và so sánh với phần mở rộng, giữ cho logic kiểm tra MIME type tập trung và dễ quản lý.
#     """
#     def check_file_mime(self, file, mime):
#         file_content = file.read(1024)  # Đọc một phần file để kiểm tra MIME type
#         file_mime_type = mime.from_buffer(file_content)
#         file.seek(0)  # Đặt lại con trỏ của file về đầu
#
#         file_extension = file.name.split('.')[-1].lower()
#         if file_extension in self.ALLOWED_MIME_TYPES:
#             expected_mime_part = self.ALLOWED_MIME_TYPES[file_extension]
#             if expected_mime_part not in file_mime_type:
#                 return f"File {file.name} type does not match its extension."
#         else:
#             return f"Unsupported file type for {file.name}."
#
#         return None

# from django.middleware.csrf import get_token
# class CustomCSRFMiddleware(MiddlewareMixin):
#     def process_request(self, request):
#         # Skip CSRF validation for safe methods and unauthenticated requests
#         if request.method in ('GET', 'HEAD', 'OPTIONS', 'TRACE'):
#             return None
#
#         # Get the CSRF token from the request header
#         csrf_token = request.headers.get('X-CSRFToken') or request.POST.get('csrfmiddlewaretoken')
#
#         # Check if the CSRF token matches the token stored in the session
#         if csrf_token != get_token(request):
#             logger.warning(f"CSRF token mismatch: {csrf_token}")
#             return JsonResponse({'error': 'CSRF token missing or incorrect.'}, status=403)
#
#         return None
