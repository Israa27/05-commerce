import random
import string
from typing import List

from django.contrib.auth import get_user_model
from django.db.models import Q
from django.shortcuts import get_object_or_404
from ninja import Router
from pydantic import UUID4

from account.authorization import GlobalAuth
from commerce.models import *
from commerce.schemas import *
from config.utils.schemas import MessageOut

products_controller = Router(tags=['products'])
address_controller = Router(tags=['addresses'])
vendor_controller = Router(tags=['vendors'])
order_controller = Router(tags=['orders'])

User = get_user_model()

@vendor_controller.get('', response=List[VendorOut])
def list_vendors(request):
    return Vendor.objects.all()


@products_controller.get('', response={
    200: List[ProductOut],
    404: MessageOut
})
def list_products(
        request, *,
        q: str = None,
        price_from: int = None,
        price_to: int = None,
        vendor=None,
):
    products_qs = Product.objects.filter(is_active=True).select_related('merchant', 'vendor', 'category', 'label')

    if not products_qs:
        return 404, {'detail': 'No products found'}

    if q:
        products_qs = products_qs.filter(
            Q(name__icontains=q) | Q(description__icontains=q)
        )

    if price_from:
        products_qs = products_qs.filter(discounted_price__gte=price_from)

    if price_to:
        products_qs = products_qs.filter(discounted_price__lte=price_to)

    if vendor:
        products_qs = products_qs.filter(vendor_id=vendor)

    return products_qs


"""
# product = Product.objects.all().select_related('merchant', 'category', 'vendor', 'label')
    # print(product)
    #
    # order = Product.objects.all().select_related('address', 'user').prefetch_related('items')

    # try:
    #     one_product = Product.objects.get(id='8d3dd0f1-2910-457c-89e3-1b0ed6aa720a')
    # except Product.DoesNotExist:
    #     return {"detail": "Not found"}
    # print(one_product)
    #
    # shortcut_function = get_object_or_404(Product, id='8d3dd0f1-2910-457c-89e3-1b0ed6aa720a')
    # print(shortcut_function)

    # print(type(product))
    # print(product.merchant.name)
    # print(type(product.merchant))
    # print(type(product.category))


Product <- Merchant, Label, Category, Vendor

Retrieve 1000 Products form DB

products = Product.objects.all()[:1000] (select * from product limit 1000)

for p in products:
    print(p)
    
for every product, we retrieve (Merchant, Label, Category, Vendor) records

Merchant.objects.get(id=p.merchant_id) (select * from merchant where id = 'p.merchant_id')
Label.objects.get(id=p.label_id) (select * from merchant where id = 'p.label_id')
Category.objects.get(id=p.category_id) (select * from merchant where id = 'p.category_id')
Vendor.objects.get(id=p.vendor_id) (select * from merchant where id = 'p.vendor_id')

4*1000+1

Solution: Eager loading

products = (select * from product limit 1000)

mids = [p1.merchant_id, p2.merchant_id, ...]
[p1.label_id, p2.label_id, ...]
.
.
.

select * from merchant where id in (mids) * 4 for (label, category and vendor)

4+1

"""


@address_controller.get('')
def list_addresses(request):
    pass


# @products_controller.get('categories', response=List[CategoryOut])
# def list_categories(request):
#     return Category.objects.all()


@address_controller.get('cities', response={
    200: List[CitiesOut],
    404: MessageOut
})
def list_cities(request):
    cities_qs = City.objects.all()

    if cities_qs:
        return cities_qs

    return 404, {'detail': 'No cities found'}


@address_controller.get('cities/{id}', response={
    200: CitiesOut,
    404: MessageOut
})
def retrieve_city(request, id: UUID4):
    return get_object_or_404(City, id=id)


@address_controller.post('cities', response={
    201: CitiesOut,
    400: MessageOut
})
def create_city(request, city_in: CitySchema):
    city = City(**city_in.dict())
    city.save()
    return 201, city


@address_controller.put('cities/{id}', response={
    200: CitiesOut,
    400: MessageOut
})
def update_city(request, id: UUID4, city_in: CitySchema):
    city = get_object_or_404(City, id=id)
    city.name = city_in.name
    city.save()
    return 200, city


@address_controller.delete('cities/{id}', response={
    204: MessageOut
})
def delete_city(request, id: UUID4):
    city = get_object_or_404(City, id=id)
    city.delete()
    return 204, {'detail': ''}


@order_controller.get('cart', response={
    200: List[ItemOut],
    404: MessageOut
},auth=GlobalAuth())
def view_cart(request):
    cart_items = Item.objects.filter(user=User.objects.get(id=request.auth['pk']), ordered=False)

    if cart_items:
        return cart_items

    return 404, {'detail': 'Your cart is empty, go shop like crazy!'}


@order_controller.post('add-to-cart', response={
    200: MessageOut,
    # 400: MessageOut
},auth=GlobalAuth())
def add_update_cart(request, item_in: ItemCreate):
    try:
        item = Item.objects.get(product_id=item_in.product_id, user=User.objects.get(id=request.auth['pk']))
        item.item_qty += 1
        item.save()
    except Item.DoesNotExist:
        Item.objects.create(**item_in.dict(), user=User.objects.get(id=request.auth['pk']))

    return 200, {'detail': 'Added to cart successfully'}


@order_controller.post('item/{id}/reduce-quantity', response={
    200: MessageOut,
},auth=GlobalAuth())
def reduce_item_quantity(request, id: UUID4):
    item = get_object_or_404(Item, id=id, user=User.objects.get(id=request.auth['pk']))
    if item.item_qty <= 1:
        item.delete()
        return 200, {'detail': 'Item deleted!'}
    item.item_qty -= 1
    item.save()

    return 200, {'detail': 'Item quantity reduced successfully!'}


@order_controller.delete('item/{id}', response={
    204: MessageOut
},auth=GlobalAuth())
def delete_item(request, id: UUID4):
    item = get_object_or_404(Item, id=id, user=User.objects.get(id=request.auth['pk']))
    item.delete()

    return 204, {'detail': 'Item deleted!'}


#-----------address----------------

@order_controller.get('address', response={
    200: List[AddressOut],
    404: MessageOut
})
def list_address(request):
    address_qs =Address.objects.all()

    if address_qs:
        return address_qs

    return 404, {'detail': 'No address found'}


@address_controller.get('order_address/{id}', response={
    200: AddressOut,
    404: MessageOut
})
def retrieve_address(request, id: UUID4):
    return get_object_or_404(Address, id=id)


@order_controller.post('order_address', response={
    201: AddressOut,
    400: MessageOut
},auth=GlobalAuth())
def create_address(request, address_in:AddressSchema):
    city = City(**address_in.city.dict())
    city.save()
    address=Address.objects.create(address1=address_in.address1,address2=address_in.address2,
    phone=address_in.phone,
    work_address=address_in.work_address,
    city=city,user=User.objects.get(id=request.auth['pk']))
    address.save()
    return 201, address


@order_controller.put('order_address/{id}', response={
    200: AddressOut,
    400: MessageOut
})
def update_address(request, id: UUID4, address_in:AddressSchema):
    city = City(**address_in.city.dict())
    city.save()
    address = get_object_or_404(Address, id=id)
    address.address1 = address_in.address1
    address.address2 = address_in.address2
    address.phone = address_in.phone
    address.work_address=address_in.work_address 
    address.city=city
    address.save()
    return 200, address


@order_controller.delete('order_address/{id}', response={
    204: MessageOut
})
def delete_city(request, id: UUID4):
    address = get_object_or_404(Address, id=id)
    address.delete()
    return 204, {'detail': ''}


#-----------create-order----------------
def generate_ref_code():
    return ''.join(random.sample(string.ascii_letters + string.digits, 6))


@order_controller.post('create-order', response=MessageOut,auth=GlobalAuth())
def create_order(request):
    order_qs = Order.objects.create(
        user=User.objects.first(),
        status=OrderStatus.objects.get(is_default=True),
        ref_code=generate_ref_code(),
        ordered=False,
    )

    user_items = Item.objects.filter(user=User.objects.get(id=request.auth['pk'])).filter(ordered=False)

    order_qs.items.add(*user_items)
    order_qs.total = order_qs.order_total
    user_items.update(ordered=True)
    order_qs.save()

    return {'detail': 'order created successfully'}
       

#----------------checkout-----------

@order_controller.post('checkout', response=MessageOut,auth=GlobalAuth())
def checkout(request ,order_address:CheckOut):
    order_item = Order.objects.filter(user=User.objects.get(id=request.auth['pk'])).filter(ordered=False)
    print(order_item)
    city = City(**order_address.address.city.dict())
    city.save()

    if order_item:
        order_item.note=order_address.note
        order_item.address=Address.objects.create(address1=order_address.address.address1,address2=order_address.address.address2,
        phone=order_address.address.phone,
        work_address=order_address.address.work_address,
        city=city,user=User.objects.get(id=request.auth['pk']))
        order_item.update(ordered=True)
        order_item.status=OrderStatus.objects.get(is_default=True)
        return {'detail':'done checkout'}
    
    return{'detail': 'nothing'}
