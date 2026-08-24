from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.permissions import BasePermission, IsAuthenticated, AllowAny
from django.contrib.auth.models import User, Group
from django.shortcuts import get_object_or_404
from .models import Category, MenuItem, Cart, Order, OrderItem
from .serializers import (
    CategorySerializer,
    MenuItemSerializer,
    CartSerializer,
    OrderSerializer,
    OrderItemSerializer
)
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter, OrderingFilter
from .permissions import MenuItemPermission


class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="Manager").exists()


class IsDeliveryCrew(BasePermission):
    def has_permission(self, request, view):
        return request.user.groups.filter(name="Delivery crew").exists()



class CategoriesView(generics.ListCreateAPIView):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]



class MenuItemsView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [MenuItemPermission

                          filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]

    filterset_fields = ['category', 'featured']
    search_fields = ['title']
    ordering_fields = ['price', 'title']

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsManager()]


class SingleMenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer

    def get_permissions(self):
        if self.request.method == 'GET':
            return [AllowAny()]
        return [IsManager()]



class CartView(generics.GenericAPIView):
    serializer_class = CartSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart = Cart.objects.filter(user=request.user)
        serializer = CartSerializer(cart, many=True)
        return Response(serializer.data)

    def post(self, request):
        menuitem = get_object_or_404(MenuItem, id=request.data.get('menuitem'))
        quantity = int(request.data.get('quantity', 1))

        cart_item, created = Cart.objects.get_or_create(
            user=request.user,
            menuitem=menuitem,
            defaults={
                'quantity': quantity,
                'unit_price': menuitem.price,
                'price': menuitem.price * quantity
            }
        )

        if not created:
            cart_item.quantity += quantity
            cart_item.price = cart_item.quantity * cart_item.unit_price
            cart_item.save()

        return Response({"message": "Item added to cart"}, status=status.HTTP_201_CREATED)

    def delete(self, request):
        Cart.objects.filter(user=request.user).delete()
        return Response({"message": "Cart cleared"}, status=status.HTTP_200_OK)



class OrdersView(generics.GenericAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    filter_backends = [DjangoFilterBackend, OrderingFilter]
    ordering_fields = ['date', 'total', 'status']

    def get(self, request):
        user = request.user

        if user.groups.filter(name="Manager").exists():
            orders = Order.objects.all()
        elif user.groups.filter(name="Delivery crew").exists():
            orders = Order.objects.filter(delivery_crew=user)
        else:
            orders = Order.objects.filter(user=user)

        serializer = OrderSerializer(orders, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = request.user
        cart_items = Cart.objects.filter(user=user)

        if not cart_items.exists():
            return Response({"error": "Cart is empty"}, status=400)

        total = sum(item.price for item in cart_items)

        order = Order.objects.create(user=user, total=total)

        for item in cart_items:
            OrderItem.objects.create(
                order=order,
                menuitem=item.menuitem,
                quantity=item.quantity,
                unit_price=item.unit_price,
                price=item.price
            )

        cart_items.delete()

        return Response({"message": "Order created"}, status=201)


class SingleOrderView(generics.GenericAPIView):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        if request.user != order.user and not request.user.groups.filter(name="Manager").exists():
            return Response({"error": "Not allowed"}, status=403)

        items = OrderItem.objects.filter(order=order)
        serializer = OrderItemSerializer(items, many=True)
        return Response(serializer.data)

    def patch(self, request, pk):
        order = get_object_or_404(Order, pk=pk)

        if request.user.groups.filter(name="Manager").exists():
            order.delivery_crew_id = request.data.get('delivery_crew', order.delivery_crew_id)
            order.status = request.data.get('status', order.status)
            order.save()
            return Response({"message": "Order updated"})

        elif request.user.groups.filter(name="Delivery crew").exists():
            order.status = request.data.get('status', order.status)
            order.save()
            return Response({"message": "Status updated"})

        return Response({"error": "Not allowed"}, status=403)

    def delete(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({"error": "Not allowed"}, status=403)

        order = get_object_or_404(Order, pk=pk)
        order.delete()
        return Response({"message": "Order deleted"}, status=200)



class ManagerUsersView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        group = Group.objects.get(name="Manager")
        users = group.user_set.all()
        return Response([user.username for user in users])

    def post(self, request):
        user = get_object_or_404(User, id=request.data.get('user_id'))
        group = Group.objects.get(name="Manager")
        group.user_set.add(user)
        return Response({"message": "User added to Manager"}, status=201)


class ManagerUserDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def delete(self, request, userId):
        user = get_object_or_404(User, id=userId)
        group = Group.objects.get(name="Manager")
        group.user_set.remove(user)
        return Response({"message": "User removed"}, status=200)


class DeliveryCrewUsersView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def get(self, request):
        group = Group.objects.get(name="Delivery crew")
        users = group.user_set.all()
        return Response([user.username for user in users])

    def post(self, request):
        user = get_object_or_404(User, id=request.data.get('user_id'))
        group = Group.objects.get(name="Delivery crew")
        group.user_set.add(user)
        return Response({"message": "User added to Delivery Crew"}, status=201)


class DeliveryCrewUserDetailView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated, IsManager]

    def delete(self, request, userId):
        user = get_object_or_404(User, id=userId)
        group = Group.objects.get(name="Delivery crew")
        group.user_set.remove(user)
        return Response({"message": "User removed"}, status=200)
