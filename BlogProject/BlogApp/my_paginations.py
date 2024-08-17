from rest_framework.pagination import PageNumberPagination

class UserPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang


class JobPostPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang


class JobApplicationPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang


class CategoryPagination(PageNumberPagination):
    page_size = 20  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class ProductPagination(PageNumberPagination):
    page_size = 20  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class GroupPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class BannerPagination(PageNumberPagination):
    page_size = 4  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100


class BlogPagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class LikePagination(PageNumberPagination):
    page_size = 15  # Số mục trên mỗi trang
    page_size_query_param = 'page_size'
    max_page_size = 100  # Số mục tối đa trên mỗi trang

class CommentPagination(PageNumberPagination):
    page_size = 20  # Số lượng bình luận trên mỗi trang
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