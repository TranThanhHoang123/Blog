from rest_framework.pagination import PageNumberPagination

class UserPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang


class BlogPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang