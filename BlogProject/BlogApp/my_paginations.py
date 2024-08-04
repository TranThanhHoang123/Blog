from rest_framework.pagination import PageNumberPagination

class UserPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang


class BlogPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class LikePagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class CommentPagination(PageNumberPagination):
    page_size = 5  # Số lượng bình luận trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100

class CompanyPagination(PageNumberPagination):
    page_size = 20  # Số lượng bình luận trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100

class RecruitmentPagination(PageNumberPagination):
    page_size = 10  # Số lượng items mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100

class JobApplicationPagination(PageNumberPagination):
    page_size = 10  # Số lượng items mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100