"""Schema GraphQL dla sklepu rozproszonego pomiędzy Katowice i Kraków."""

import graphene
from pony.orm import db_session

from .models import list_inventory, list_orders, list_products
from .mutations import Mutation


class ProductType(graphene.ObjectType):
    id = graphene.Int()
    sku = graphene.String()
    name = graphene.String()
    description = graphene.String()
    price = graphene.Float()
    active = graphene.Boolean()

    def resolve_id(root, info):
        with db_session:
            return root.id

    def resolve_sku(root, info):
        with db_session:
            return root.sku

    def resolve_name(root, info):
        with db_session:
            return root.name

    def resolve_description(root, info):
        with db_session:
            return root.description

    def resolve_price(root, info):
        with db_session:
            return root.price

    def resolve_active(root, info):
        with db_session:
            return root.active


class InventoryType(graphene.ObjectType):
    id = graphene.Int()
    node = graphene.String()
    product = graphene.Field(ProductType)
    quantity = graphene.Int()

    def resolve_id(root, info):
        with db_session:
            return root.id

    def resolve_node(root, info):
        return root.node

    def resolve_product(root, info):
        with db_session:
            return root.product

    def resolve_quantity(root, info):
        with db_session:
            return root.quantity


class OrderItemType(graphene.ObjectType):
    id = graphene.Int()
    product = graphene.Field(ProductType)
    quantity = graphene.Int()
    unit_price = graphene.Float()

    def resolve_id(root, info):
        with db_session:
            return root.id

    def resolve_product(root, info):
        with db_session:
            return root.product

    def resolve_quantity(root, info):
        with db_session:
            return root.quantity

    def resolve_unit_price(root, info):
        with db_session:
            return root.unit_price


class OrderType(graphene.ObjectType):
    id = graphene.Int()
    node = graphene.String()
    customer_name = graphene.String()
    status = graphene.String()
    total = graphene.Float()
    items = graphene.List(OrderItemType)

    def resolve_id(root, info):
        with db_session:
            return root.id

    def resolve_node(root, info):
        return root.node

    def resolve_customer_name(root, info):
        with db_session:
            return root.customer_name

    def resolve_status(root, info):
        with db_session:
            return root.status

    def resolve_total(root, info):
        with db_session:
            return root.total

    def resolve_items(root, info):
        with db_session:
            return root.items


class Query(graphene.ObjectType):
    products = graphene.List(ProductType)
    inventory = graphene.List(InventoryType, node=graphene.String())
    orders = graphene.List(OrderType, node=graphene.String())

    def resolve_products(root, info):
        return list_products()

    def resolve_inventory(root, info, node=None):
        return list_inventory(node)

    def resolve_orders(root, info, node=None):
        return list_orders(node)


schema = graphene.Schema(query=Query, mutation=Mutation)