from django.db.models import Sum, Count, Max, Min, Avg
from rest_framework import viewsets, generics, status, permissions
from rest_framework.response import Response
from . import serializers, my_paginations, my_generics, filters, utils, my_permissions
from rest_framework.decorators import action
from .utils import *
from django.utils.dateparse import parse_datetime
from rest_framework import status
from .models import *
from django.utils import timezone

timezone.get_current_timezone()  # Lấy múi giờ hiện tại của hệ thống


class StatsView(viewsets.ViewSet):
    queryset = None
    serializer_class = None
    permission_classes = [my_permissions.IsAdminOrManager]

    @action(methods=['get'], url_path='user', detail=False)
    def user(self, request):
        stats = User.objects.filter(is_active=True).aggregate(
            total_users=Count('id'),
            admin_count=Count('id', filter=Q(groups__name='admin')),
            manager_count=Count('id', filter=Q(groups__name='manager')),
            no_group_count=Count('id', filter=~Q(groups__name__in=['admin', 'manager']))
        )
        return Response(stats, status.HTTP_200_OK)

    # thống kê blog
    @action(methods=['get'], url_path='blog-general', detail=False)
    def blog_post(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')

        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))

        # Tính toán tổng số blog, tổng số lượt like và comment distinct
        stats = Blog.objects.filter(
            created_date__range=[start_date, end_date]
        ).aggregate(
            # tổng bài viêt
            total_blogs=Count('id', distinct=True),
            # tổng tất cả lượt like của tất cả bài viêt
            total_likes=Count('like__id', distinct=True),
            # tổng tất cả lượt comment của tất cả bài viêt
            total_comments=Count('comment__id', distinct=True)
        )
        # tổng bài viêt
        total_blogs = stats['total_blogs']
        total_interactions = stats['total_likes'] + stats['total_comments']
        # Trung bình lượt like trên bài viết
        average_likes_per_blog = stats['total_likes'] / total_blogs if total_blogs > 0 else 0
        # Trung bình lượt comment trên mỗi bài viết
        average_comments_per_blog = stats['total_comments'] / total_blogs if total_blogs > 0 else 0
        # tring bình độ tương tác mỗi bài viết
        average_interactions_per_blog = total_interactions / total_blogs if total_blogs > 0 else 0

        response_data = {
            'total_blogs': stats['total_blogs'],
            'total_likes': stats['total_likes'],
            'total_comments': stats['total_comments'],
            'total_interactions': total_interactions,
            'average_likes_per_blog': average_likes_per_blog,
            'average_comments_per_blog': average_comments_per_blog,
            'average_interactions_per_blog': average_interactions_per_blog
        }

        return Response(response_data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='product-general', detail=False)
    def product_general(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))
        # Tính tổng số sản phẩm, tổng tiền, và số lượng sản phẩm theo fettle và condition
        stats = Product.objects.filter(
            created_date__range=[start_date, end_date]
        ).aggregate(
            total_products=Count('id', distinct=True),
            total_price=Sum('price'),
            in_stock_products=Count('id', filter=Q(fettle='in_stock')),
            out_of_stock_products=Count('id', filter=Q(fettle='out_of_stock')),
            new_products=Count('id', filter=Q(condition='new')),
            used_products=Count('id', filter=Q(condition='used')),
        )

        return Response(stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='product-category-general', detail=False)
    def product_category_general(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))
        # Tính tổng số lượng sản phẩm và tổng tiền trong mỗi danh mục, kể cả khi không có sản phẩm nào
        category_stats = Category.objects.annotate(
            total_products=Count(
                'productcategory__product_id',
                filter=Q(productcategory__product__created_date__range=[start_date, end_date]),
                distinct=True
            ),
            total_price=Sum(
                'productcategory__product__price',
                filter=Q(productcategory__product__created_date__range=[start_date, end_date])
            )
        ).values('name', 'total_products', 'total_price')

        return Response(category_stats, status=status.HTTP_200_OK)
    @action(methods=['get'], url_path='product-category-specific', detail=False)
    def product_category_specific(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        category_name = request.query_params.get('category_name')
        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))
        if not category_name:
            return Response({"detail": "category_name is required"}, status=status.HTTP_400_BAD_REQUEST)

        # Tính tổng số lượng sản phẩm và tổng tiền trong danh mục cụ thể theo khoảng thời gian
        category_stats = ProductCategory.objects.filter(
            product__created_date__range=[start_date, end_date],
            category__name=category_name
        ).aggregate(
            total_products=Count('product_id'),
            total_price=Sum('product__price')
        )

        return Response(category_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='job-application-general', detail=False)
    def job_application_stats(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))

        # Tính số lượng theo các trạng thái
        job_application_total_stats = JobApplication.objects.filter(created_date__range=[start_date, end_date]).aggregate(
            total_pending=Count('id', filter=Q(status='pending')),
            total_approved=Count('id', filter=Q(status='approved')),
            total_rejected=Count('id', filter=Q(status='rejected')),
        )

        # Tổng số lượng JobApplication bằng cách cộng ba trạng thái
        job_application_total_stats['total_applications'] = job_application_total_stats['total_pending'] + job_application_total_stats['total_approved'] + job_application_total_stats['total_rejected']
        # Trả về kết quả thống kê
        return Response(job_application_total_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='job-post-general', detail=False)
    def job_post_general(self, request):
        start_date = request.query_params.get('start_date')
        end_date = request.query_params.get('end_date')
        start_date = timezone.make_aware(parse_datetime(start_date))
        end_date = timezone.make_aware(parse_datetime(end_date))

        data=None

        return Response(data, status=status.HTTP_200_OK)