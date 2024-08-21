# myapp/middleware.py

from django.conf import settings
from django.http import JsonResponse
from django.utils.deprecation import MiddlewareMixin


class FileSizeLimitMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # Lấy kích thước tối đa từ settings
        max_file_size = getattr(settings, 'DATA_UPLOAD_MAX_MEMORY_SIZE', 5 * 1024 * 1024)  # 5MB mặc định

        if request.method in ['POST', 'PATCH'] and request.FILES:
            for file in request.FILES.values():
                # Kiểm tra kích thước file
                if file.size > max_file_size:
                    return JsonResponse(
                        {
                            'detail': f'File size exceeds the limit. Maximum allowed size is {max_file_size // (1024 * 1024)}MB.'},
                        status=400
                    )
        return None

import os
import re
class SanitizeFilenameMiddleware(MiddlewareMixin):
    def process_request(self, request):
        if request.FILES:
            for file_key, file in request.FILES.items():
                # Lấy phần mở rộng của tệp
                file_extension = os.path.splitext(file.name)[1]

                # Xóa tất cả các ký tự đặc biệt
                sanitized_name = re.sub(r'[^\w\s-]', '', os.path.splitext(file.name)[0])

                # Xóa các dấu cách thừa hoặc dấu gạch ngang ở đầu/cuối
                sanitized_name = re.sub(r'[-\s]+', '-', sanitized_name).strip('-_')

                # Tạo tên tệp mới với phần mở rộng cũ
                sanitized_name += file_extension

                # Cập nhật tên tệp trong request.FILES
                request.FILES[file_key].name = sanitized_name
