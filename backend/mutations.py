import graphene
from pony.orm import db_session

from .models import NODES, get_node


class ProductInput(graphene.InputObjectType):
    sku = graphene.String(required=True)
    name = graphene.String(required=True)
    description = graphene.String()
    price = graphene.Float(required=True)


class OrderItemInput(graphene.InputObjectType):
    sku = graphene.String(required=True)
    quantity = graphene.Int(required=True)


class ProductPayload(graphene.ObjectType):
    id = graphene.Int()
    sku = graphene.String()
    name = graphene.String()
    description = graphene.String()
    price = graphene.Float()
    active = graphene.Boolean()


class InventoryPayload(graphene.ObjectType):
    node = graphene.String()
    sku = graphene.String()
    quantity = graphene.Int()


class OrderPayload(graphene.ObjectType):
    id = graphene.Int()
    node = graphene.String()
    total = graphene.Float()
    status = graphene.String()


class CreateProduct(graphene.Mutation):
    class Arguments:
        product = ProductInput(required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    product = graphene.Field(ProductPayload)

    @staticmethod
    def mutate(root, info, product):
        first_product = None
        for node in NODES.values():
            with db_session:
                entity = node.Product(
                    sku=product["sku"],
                    name=product["name"],
                    description=product.get("description", ""),
                    price=product["price"],
                )
                node.Inventory(product=entity, quantity=0)
                if first_product is None:
                    first_product = entity
        return CreateProduct(
            ok=True,
            message="Produkt zapisano w obu węzłach",
            product=first_product,
        )


class UpdateInventory(graphene.Mutation):
    class Arguments:
        node = graphene.String(required=True)
        sku = graphene.String(required=True)
        quantity = graphene.Int(required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    inventory = graphene.Field(InventoryPayload)

    @staticmethod
    def mutate(root, info, node, sku, quantity):
        selected = get_node(node)
        with db_session:
            product = selected.Product.get(sku=sku)
            if product is None:
                raise ValueError(f"Nie znaleziono produktu o SKU {sku}")
            inventory = selected.Inventory.get(product=product)
            if inventory is None:
                inventory = selected.Inventory(product=product, quantity=quantity)
            else:
                inventory.quantity = quantity
            data = InventoryPayload(
                node=selected.name,
                sku=sku,
                quantity=inventory.quantity,
            )
        return UpdateInventory(ok=True, message="Stan magazynowy zaktualizowany", inventory=data)


class CreateOrder(graphene.Mutation):
    class Arguments:
        node = graphene.String(required=True)
        customer_name = graphene.String(required=True)
        items = graphene.List(OrderItemInput, required=True)

    ok = graphene.Boolean()
    message = graphene.String()
    order = graphene.Field(OrderPayload)

    @staticmethod
    def mutate(root, info, node, customer_name, items):
        selected = get_node(node)
        with db_session:
            order = selected.Order(customer_name=customer_name, status="NEW", total=0)
            total = 0.0
            for item in items:
                product = selected.Product.get(sku=item["sku"])
                inventory = selected.Inventory.get(product=product) if product else None
                if product is None or inventory is None:
                    raise ValueError(f"Produkt {item['sku']} nie istnieje w węźle {selected.name}")
                if inventory.quantity < item["quantity"]:
                    raise ValueError(f"Brak wystarczającej ilości produktu {item['sku']}")
                inventory.quantity -= item["quantity"]
                selected.OrderItem(
                    order=order,
                    product=product,
                    quantity=item["quantity"],
                    unit_price=product.price,
                )
                total += product.price * item["quantity"]
            order.total = total
            result = OrderPayload(
                id=order.id,
                node=selected.name,
                total=total,
                status=order.status,
            )
        return CreateOrder(ok=True, message="Zamówienie utworzone", order=result)


class DeleteProduct(graphene.Mutation):
    class Arguments:
        sku = graphene.String(required=True)

    ok = graphene.Boolean()
    message = graphene.String()

    @staticmethod
    def mutate(root, info, sku):
        for node in NODES.values():
            with db_session:
                product = node.Product.get(sku=sku)
                if product:
                    product.active = False
        return DeleteProduct(ok=True, message="Produkt oznaczono jako nieaktywny w obu węzłach")


class Mutation(graphene.ObjectType):
    create_product = CreateProduct.Field()
    update_inventory = UpdateInventory.Field()
    create_order = CreateOrder.Field()
    delete_product = DeleteProduct.Field()