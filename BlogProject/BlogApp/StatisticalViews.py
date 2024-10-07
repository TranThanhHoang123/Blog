from django.db.models import Sum, Count, Q, Avg
from django.db.models.functions import TruncDate, TruncMonth, TruncQuarter,TruncYear
from rest_framework import viewsets
from rest_framework.response import Response
from . import my_permissions
from rest_framework.decorators import action
from .utils import *
from django.utils.dateparse import parse_datetime
from rest_framework import status
from .models import *
from django.utils import timezone
from django.conf import settings



from django.utils.cache import patch_cache_control
from django.core.cache import cache
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page


class StatsView(viewsets.ViewSet):
    queryset = None
    serializer_class = None
    permission_classes = [my_permissions.IsAdminOrManager]

    @action(methods=['get'], url_path='user', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def user(self, request):
        cache_key = 'user_stats'
        stats = cache.get(cache_key)
        if not stats:
            stats = User.objects.filter(is_active=True).aggregate(
                total_users=Count('id'),
                admin_count=Count('id', filter=Q(groups__name='admin')),
                manager_count=Count('id', filter=Q(groups__name='manager')),
                no_group_count=Count('id', filter=~Q(groups__name__in=['admin', 'manager']))
            )
            cache.set(cache_key, stats, timeout=settings.STATICAL_CACHE_TIME)  # Cache kết quả cho 10 phút

        return Response(stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='blog-general', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def blog_post(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        frequency = request.query_params.get('frequency', 'day')  # 'day', 'month', 'quarter', 'year'

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)
        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)
        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        cache_key = f'blog_stats_{start_date.isoformat()}_{end_date.isoformat()}'
        stats = cache.get(cache_key)

        if not stats:
            stats = Blog.objects.filter(
                created_date__range=[start_date, end_date]
            ).aggregate(
                total_blogs=Count('id', distinct=True),
                total_likes=Count('like__id', distinct=True),
                total_comments=Count('comment__id', distinct=True)
            )

            total_blogs = stats['total_blogs']
            total_interactions = stats['total_likes'] + stats['total_comments']
            average_likes_per_blog = stats['total_likes'] / total_blogs if total_blogs > 0 else 0
            average_comments_per_blog = stats['total_comments'] / total_blogs if total_blogs > 0 else 0
            average_interactions_per_blog = total_interactions / total_blogs if total_blogs > 0 else 0

            # Chọn tần suất dựa trên tham số frequency
            if frequency == 'month':
                truncate = TruncMonth
            elif frequency == 'quarter':
                truncate = TruncQuarter
            elif frequency == 'year':
                truncate = TruncYear
            else:  # 'day' là giá trị mặc định
                truncate = TruncDate

            # Tính tần suất bài viết
            blog_counts = Blog.objects.filter(
                created_date__range=[start_date, end_date]
            ).annotate(
                date=truncate('created_date')
            ).values('date').annotate(
                blog_count=Count('id')
            ).order_by('date')

            # Định dạng dữ liệu ngày tháng theo tần suất
            formatted_blog_counts = []
            for entry in blog_counts:
                date = entry['date']
                count = entry['blog_count']
                formatted_blog_counts.append({
                    'date': date.strftime('%Y-%m-%d') if frequency == 'day' else
                    date.strftime('%Y-%m') if frequency == 'month' else
                    f'{date.year}-Q{((date.month - 1) // 3) + 1}' if frequency == 'quarter' else
                    date.strftime('%Y'),
                    'count': count
                })

            response_data = {
                'total_blogs': stats['total_blogs'],
                'total_likes': stats['total_likes'],
                'total_comments': stats['total_comments'],
                'total_interactions': total_interactions,
                'average_likes_per_blog': average_likes_per_blog,
                'average_comments_per_blog': average_comments_per_blog,
                'average_interactions_per_blog': average_interactions_per_blog,
                'daily_blog_counts': list(formatted_blog_counts),  # Convert QuerySet to list
            }
            cache.set(cache_key, response_data, timeout=settings.STATICAL_CACHE_TIME)  # Cache kết quả cho 10 phút
        else:
            response_data = stats

        return Response(response_data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='product-general', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def product_general(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        frequency = request.query_params.get('frequency', 'day')  # 'day', 'month', 'quarter', 'year'

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)

        cache_key = f'product_stats_{start_date.isoformat()}_{end_date.isoformat()}_{frequency}'
        stats = cache.get(cache_key)

        if not stats:
            # Tổng hợp số liệu sản phẩm
            aggregate_stats = Product.objects.filter(
                created_date__range=[start_date, end_date]
            ).aggregate(
                total_products=Count('id', distinct=True),
                total_price=Sum('price'),
                in_stock_products=Count('id', filter=Q(fettle='in_stock')),
                out_of_stock_products=Count('id', filter=Q(fettle='out_of_stock')),
                new_products=Count('id', filter=Q(condition='new')),
                used_products=Count('id', filter=Q(condition='used')),
            )

            # Chọn tần suất dựa trên tham số frequency
            if frequency == 'month':
                truncate = TruncMonth
            elif frequency == 'quarter':
                truncate = TruncQuarter
            elif frequency == 'year':
                truncate = TruncYear
            else:  # 'day' là giá trị mặc định
                truncate = TruncDate

            # Tính tần suất sản phẩm
            product_counts = Product.objects.filter(
                created_date__range=[start_date, end_date]
            ).annotate(
                date=truncate('created_date')
            ).values('date').annotate(
                product_count=Count('id')
            ).order_by('date')

            # Định dạng dữ liệu ngày tháng theo tần suất
            formatted_product_counts = []
            for entry in product_counts:
                date = entry['date']
                count = entry['product_count']
                formatted_product_counts.append({
                    'date': date.strftime('%Y-%m-%d') if frequency == 'day' else
                    date.strftime('%Y-%m') if frequency == 'month' else
                    f'{date.year}-Q{((date.month - 1) // 3) + 1}' if frequency == 'quarter' else
                    date.strftime('%Y'),
                    'count': count
                })

            response_data = {
                'total_products': aggregate_stats['total_products'],
                'total_price': aggregate_stats['total_price'],
                'in_stock_products': aggregate_stats['in_stock_products'],
                'out_of_stock_products': aggregate_stats['out_of_stock_products'],
                'new_products': aggregate_stats['new_products'],
                'used_products': aggregate_stats['used_products'],
                'product_counts': list(formatted_product_counts),  # Convert QuerySet to list and format
            }
            cache.set(cache_key, response_data, timeout=settings.STATICAL_CACHE_TIME)  # Cache kết quả cho 10 phút
        else:
            response_data = stats

        return Response(response_data, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='product-category-general', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def product_category_general(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        frequency = request.query_params.get('frequency', 'day')  # 'day', 'month', 'quarter', 'year'

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)

        cache_key = f'category_stats_{start_date.isoformat()}_{end_date.isoformat()}_{frequency}'
        category_stats = cache.get(cache_key)

        if not category_stats:
            # Chọn tần suất dựa trên tham số frequency
            if frequency == 'month':
                truncate = TruncMonth
            elif frequency == 'quarter':
                truncate = TruncQuarter
            elif frequency == 'year':
                truncate = TruncYear
            else:  # 'day' là giá trị mặc định
                truncate = TruncDate

            # Tổng hợp số liệu theo category
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
            ).values('id', 'name', 'total_products', 'total_price')

            # Lấy tần suất theo category và format dữ liệu
            formatted_category_stats = []
            for category in category_stats:
                # Lấy tần suất sản phẩm cho từng category
                product_counts = Product.objects.filter(
                    productcategory__category_id=category['id'],
                    created_date__range=[start_date, end_date]
                ).annotate(
                    date=truncate('created_date')
                ).values('date').annotate(
                    product_count=Count('id')
                ).order_by('date')

                # Định dạng dữ liệu ngày tháng theo tần suất
                formatted_product_counts = []
                for entry in product_counts:
                    date = entry['date']
                    count = entry['product_count']
                    formatted_product_counts.append({
                        'date': date.strftime('%Y-%m-%d') if frequency == 'day' else
                        date.strftime('%Y-%m') if frequency == 'month' else
                        f'{date.year}-Q{((date.month - 1) // 3) + 1}' if frequency == 'quarter' else
                        date.strftime('%Y'),
                        'product_count': count
                    })

                # Thêm dữ liệu đã định dạng vào kết quả cuối cùng
                formatted_category_stats.append({
                    'name': category['name'],
                    'total_products': category['total_products'],
                    'total_price': category['total_price'],
                    'product_counts': formatted_product_counts if formatted_product_counts else None
                })

            cache.set(cache_key, formatted_category_stats,
                      timeout=settings.STATICAL_CACHE_TIME)  # Cache kết quả cho 10 phút
        else:
            formatted_category_stats = category_stats

        return Response(formatted_category_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='job-application-general', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def job_application_stats(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        frequency = request.query_params.get('frequency', 'day')  # 'day', 'month', 'quarter', 'year'

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        # Chuyển đổi thành timezone-aware datetime
        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)

        cache_key = f'job_application_stats_{start_date.isoformat()}_{end_date.isoformat()}_{frequency}'
        job_application_stats = cache.get(cache_key)

        if not job_application_stats:
            # Chọn tần suất dựa trên tham số frequency
            if frequency == 'month':
                truncate = TruncMonth
            elif frequency == 'quarter':
                truncate = TruncQuarter
            elif frequency == 'year':
                truncate = TruncYear
            else:  # 'day' là giá trị mặc định
                truncate = TruncDate

            # Tổng hợp số liệu ứng tuyển theo status
            job_application_total_stats = JobApplication.objects.filter(
                created_date__range=[start_date, end_date]).aggregate(
                total_pending=Count('id', filter=Q(status='pending')),
                total_approved=Count('id', filter=Q(status='approved')),
                total_rejected=Count('id', filter=Q(status='rejected')),
            )
            job_application_total_stats['total_applications'] = job_application_total_stats['total_pending'] + \
                                                                job_application_total_stats['total_approved'] + \
                                                                job_application_total_stats['total_rejected']

            # Lấy số liệu thống kê ứng tuyển theo ngày/tháng/quý/năm
            job_application_by_date = JobApplication.objects.filter(
                created_date__range=[start_date, end_date]).annotate(
                date=truncate('created_date')
            ).values('date').annotate(
                total_pending=Count('id', filter=Q(status='pending')),
                total_approved=Count('id', filter=Q(status='approved')),
                total_rejected=Count('id', filter=Q(status='rejected')),
                total_applications=Count('id')
            ).order_by('date')

            # Định dạng dữ liệu ngày tháng theo tần suất
            formatted_job_application_stats = []
            for entry in job_application_by_date:
                date = entry['date']
                formatted_job_application_stats.append({
                    'date': date.strftime('%Y-%m-%d') if frequency == 'day' else
                    date.strftime('%Y-%m') if frequency == 'month' else
                    f'{date.year}-Q{((date.month - 1) // 3) + 1}' if frequency == 'quarter' else
                    date.strftime('%Y'),
                    'total_pending': entry['total_pending'],
                    'total_approved': entry['total_approved'],
                    'total_rejected': entry['total_rejected'],
                    'total_applications': entry['total_applications'],
                })

            # Kết hợp dữ liệu tổng và theo tần suất
            job_application_stats = {
                'total_pending':job_application_total_stats['total_pending'],
                'total_approved': job_application_total_stats['total_approved'],
                'total_rejected': job_application_total_stats['total_rejected'],
                'total_pending': job_application_total_stats['total_applications'],
                'job_application_counts': formatted_job_application_stats if formatted_job_application_stats else None
            }

            cache.set(cache_key, job_application_stats,
                      timeout=settings.STATICAL_CACHE_TIME)  # Cache kết quả cho 10 phút
        else:
            job_application_stats = job_application_stats

        return Response(job_application_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='job-post-general', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def job_post_general(self, request):
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')
        frequency = request.query_params.get('frequency', 'day')  # 'day', 'month', 'quarter', 'year'
        rank = request.query_params.get('rank', '1')
        tag_id = request.query_params.get('tag_id', None)  # Lấy tag_id từ query params

        if not rank.isdigit():
            return Response({"detail": "rank have to be a number."}, status=status.HTTP_400_BAD_REQUEST)

        rank = int(rank)

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)

        # Tạo cache key
        cache_key = f'job_post_general_{start_date.isoformat()}_{end_date.isoformat()}_{frequency}_{rank}_{tag_id}'
        job_post_general_stats = cache.get(cache_key)

        if not job_post_general_stats:
            if frequency == 'month':
                truncate = TruncMonth
            elif frequency == 'quarter':
                truncate = TruncQuarter
            elif frequency == 'year':
                truncate = TruncYear
            else:
                truncate = TruncDate

            job_posts_query = JobPost.objects.filter(created_date__range=(start_date, end_date))

            if tag_id:
                if not Tag.objects.filter(id=tag_id).exists():
                    return Response({"detail": "Tag with the given id does not exist."},
                                    status=status.HTTP_400_BAD_REQUEST)
                job_posts_query = job_posts_query.filter(jobposttag__tag__id=tag_id)

            total_job_posts = job_posts_query.count()
            total_applications = JobApplication.objects.filter(job_post__in=job_posts_query).count()
            total_approved_applications = JobApplication.objects.filter(
                job_post__in=job_posts_query, status='approved').count()
            total_rejected_applications = JobApplication.objects.filter(
                job_post__in=job_posts_query, status='rejected').count()
            total_pending_applications = JobApplication.objects.filter(
                job_post__in=job_posts_query, status='pending').count()

            offer_acceptance_rate = (
                                            total_approved_applications / total_applications) * 100 if total_applications > 0 else 0

            job_posts_by_date = job_posts_query.annotate(
                created_date_group=truncate('created_date')
            ).values('created_date_group').annotate(
                total_posts=Count('id'),
                total_applications=Count('job_applications'),
                total_approved=Count('job_applications', filter=Q(job_applications__status='approved')),
                total_rejected=Count('job_applications', filter=Q(job_applications__status='rejected')),
                total_pending=Count('job_applications', filter=Q(job_applications__status='pending')),
            ).order_by('created_date_group')

            formatted_job_post_stats = []
            for entry in job_posts_by_date:
                date = entry['created_date_group']
                formatted_job_post_stats.append({
                    'date': date.strftime('%Y-%m-%d') if frequency == 'day' else
                    date.strftime('%Y-%m') if frequency == 'month' else
                    f'{date.year}-Q{((date.month - 1) // 3) + 1}' if frequency == 'quarter' else
                    date.strftime('%Y'),
                    'total_posts': entry['total_posts'],
                    'total_applications': entry['total_applications'],
                    'total_approved': entry['total_approved'],
                    'total_rejected': entry['total_rejected'],
                    'total_pending': entry['total_pending'],
                })

            most_applied_job_posts = job_posts_query.annotate(
                application_count=Count('job_applications')
            ).order_by('-application_count')[:rank]

            approved_applications = job_posts_query.annotate(
                approved_count=Count('job_applications', filter=Q(job_applications__status='approved'))
            ).order_by('-approved_count')[:rank]

            rejected_applications = job_posts_query.annotate(
                rejected_count=Count('job_applications', filter=Q(job_applications__status='rejected'))
            ).order_by('-rejected_count')[:rank]

            job_post_general_stats = {
                'total_job_posts': total_job_posts,
                'total_applications': total_applications,
                'total_approved_applications': total_approved_applications,
                'total_rejected_applications': total_rejected_applications,
                'total_pending_applications': total_pending_applications,
                'offer_acceptance_rate': offer_acceptance_rate,
                'job_post_counts': formatted_job_post_stats if formatted_job_post_stats else None,
                'most_applied_job_posts': most_applied_job_posts.values('id', 'content', 'application_count'),
                'approved_applications': approved_applications.values('id', 'content', 'approved_count'),
                'rejected_applications': rejected_applications.values('id', 'content', 'rejected_count'),
            }

            cache.set(cache_key, job_post_general_stats, timeout=settings.STATICAL_CACHE_TIME)
        else:
            job_post_general_stats = job_post_general_stats

        return Response(job_post_general_stats, status=status.HTTP_200_OK)

    @action(methods=['get'], url_path='job-post-specific', detail=False)
    @method_decorator(cache_page(settings.STATICAL_CACHE_TIME))  # Cache cho 10 phút
    def job_post_specific(self, request):
        job_post_id = request.query_params.get('job_post_id', None)
        start_date_str = request.query_params.get('start_date')
        end_date_str = request.query_params.get('end_date')

        if not job_post_id:
            return Response({"detail": "job_post_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            job_post = JobPost.objects.get(id=job_post_id)
        except JobPost.DoesNotExist:
            return Response({"detail": "Job Post with the given id does not exist."}, status=status.HTTP_404_NOT_FOUND)

        if not start_date_str or not end_date_str:
            return Response({"detail": "Both 'start_date' and 'end_date' query parameters are required."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = parse_datetime(start_date_str)
        end_date = parse_datetime(end_date_str)

        if not start_date or not end_date:
            return Response({"detail": "Invalid 'start_date' or 'end_date' format."},
                            status=status.HTTP_400_BAD_REQUEST)

        start_date = timezone.make_aware(start_date)
        end_date = timezone.make_aware(end_date)

        # Tạo cache key
        cache_key = f'job_post_specific_{job_post_id}_{start_date.isoformat()}_{end_date.isoformat()}'
        job_post_specific_stats = cache.get(cache_key)

        if not job_post_specific_stats:
            applications_in_date_range = job_post.job_applications.filter(created_date__range=(start_date, end_date))

            total_applications = applications_in_date_range.count()
            pending_applications = applications_in_date_range.filter(status='pending').count()
            approved_applications = applications_in_date_range.filter(status='approved').count()
            rejected_applications = applications_in_date_range.filter(status='rejected').count()

            male_applications = applications_in_date_range.filter(sex=True).count()
            female_applications = applications_in_date_range.filter(sex=False).count()

            average_age = applications_in_date_range.aggregate(
                average_age=Avg('age')
            )['average_age']

            job_post_specific_stats = {
                'job_post_id': job_post.id,
                'total_applications': total_applications,
                'pending_applications': pending_applications,
                'approved_applications': approved_applications,
                'rejected_applications': rejected_applications,
                'male_applications': male_applications,
                'female_applications': female_applications,
                'average_age': average_age if average_age else None
            }

            cache.set(cache_key, job_post_specific_stats, timeout=settings.STATICAL_CACHE_TIME)
        else:
            job_post_specific_stats = job_post_specific_stats

        return Response(job_post_specific_stats, status=status.HTTP_200_OK)