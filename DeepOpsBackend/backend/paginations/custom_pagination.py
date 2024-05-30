from rest_framework.pagination import PageNumberPagination

class CustomPagination(PageNumberPagination):
    max_page_size = 10000
    page_size = 10
    page_size_query_param = 'page_size'