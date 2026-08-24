from rest_framework.permissions import BasePermission


def is_manager(user):
    return user.groups.filter(name="Manager").exists()


def is_delivery_crew(user):
    return user.groups.filter(name="Delivery crew").exists()


def is_customer(user):
    return not user.groups.exists()



class IsManager(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_manager(request.user)



class IsDeliveryCrew(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_delivery_crew(request.user)



class IsCustomer(BasePermission):
    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_customer(request.user)



class MenuItemPermission(BasePermission):

    def has_permission(self, request, view):
        if request.method == 'GET':
            return True
        return request.user.is_authenticated and is_manager(request.user)



class OrderPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated

    def has_object_permission(self, request, view, obj):
        user = request.user

        if is_manager(user):
            return True

        if is_delivery_crew(user):
            return obj.delivery_crew == user


        return obj.user == user



class CartPermission(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated



class IsManagerOnly(BasePermission):

    def has_permission(self, request, view):
        return request.user and request.user.is_authenticated and is_manager(request.user)