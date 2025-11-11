# kilibs is free software: you can redistribute it and/or modify it under the terms of
# the GNU General Public License as published by the Free Software Foundation, either
# version 3 of the License, or (at your option) any later version.
#
# kilibs is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY;
# without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR
# PURPOSE. See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with kilibs.
# If not, see < http://www.gnu.org/licenses/ >.
#
# (C) The KiCad Librarian Team

"""Class definition for the shape node."""

from __future__ import annotations

from collections.abc import Iterable, Iterator, Sequence
from typing import Generic, Self, TypeVar, cast

from KicadModTree.nodes.Node import Node
from kilibs.geom import BoundingBox, Vector2D

NodeType = TypeVar("NodeType", bound=Node)


class MultipleParentsError(RuntimeError):
    def __init__(self, message: str) -> None:
        # Call the base class constructor with the parameters it needs
        super(MultipleParentsError, self).__init__(message)


class RecursionDetectedError(RuntimeError):
    def __init__(self, message: str) -> None:
        # Call the base class constructor with the parameters it needs
        super(RecursionDetectedError, self).__init__(message)


class Container(Node, Generic[NodeType]):
    """A node class for containers."""

    def __init__(self) -> None:
        """Create a `Container`."""

        # Instance attributes:
        self._children: list[NodeType]
        """"The child nodes."""

        Node.__init__(self)
        self._children = []

    def append(self, node: NodeType) -> None:
        """Add a node as child node.

        Args:
            node: The node to add.

        Raises:
            MultipleParentsError: In case the added node already has a parent assigned.
        """
        if node._parent:
            raise MultipleParentsError("muliple parents are not allowed!")

        self._children.append(node)

        node._parent = cast(Container[Node], self)
        if (node.get_timestamp_class().get_timestamp_seed() is None) and (
            self.get_timestamp_class().get_timestamp_seed() is not None
        ):
            node.set_timestamp_seed_from_node(self)

    def extend(self, nodes: Iterable[NodeType]) -> None:
        """Append all nodes from an iterable as child nodes to the current node.

        Args:
            nodes: An iterable (like a list or generator) yielding 'Node' instances
                that will be added to this node's list of children.

        Raises:
            MultipleParentsError: If one or more of the provided nodes already have a
                parent assigned. Note that any nodes successfully added prior to the
                node causing the error will remain in this node's children list (no
                rollback is performed).
        """
        for node in nodes:
            if node._parent or node in self._children:
                raise MultipleParentsError("muliple parents are not allowed!")
            node._parent = cast(Container[Node], self)
            if (node.get_timestamp_class().get_timestamp_seed() is None) and (
                self.get_timestamp_class().get_timestamp_seed() is not None
            ):
                node.set_timestamp_seed_from_node(self)
            self._children.append(node)

    def insert(self, node: Container[NodeType]) -> None:
        """Move all child nodes from this node into the given node and append the given
        node to this node.

        Args:
            node: The node that becomes the new parent node of this node's children.
        """
        for child in self._children:
            child._parent = cast(Container[Node], node)
            node._children.append(child)
        node._parent = cast(Container[Node], self)
        self._children = [cast(NodeType, node)]

    def remove(self, node: NodeType, traverse: bool = False) -> None:
        """Remove a node from this node's list of child nodes.

        Args:
            node: The node to remove.
            traverse: If `True` then the children are recursively searched for a match
                within their children.
        """
        Container[NodeType]._remove_node(parent=self, node=node)
        if traverse:
            if node == self:
                if self._parent is not None:
                    Container[Node]._remove_node(parent=self._parent, node=node)
            else:
                for child in self._children:
                    if isinstance(child, Container):
                        cast(Container[Node], child).remove(node, traverse=True)

    def bbox(self) -> BoundingBox:
        """Get the bounding box of all the child nodes."""
        bbox = BoundingBox()
        for child in self._children:
            child_bbox = child.bbox()
            bbox.include_bbox(child_bbox)
        return bbox

    @property  # read-only via getter-only and read-only return type `Sequence`
    def children(self) -> Sequence[NodeType]:
        """Return all the children of this node.

        Note:
            Nodes that are children of a transformation node (such as
            :py:class:`Rotation` or :py:class:`Translation`) are copied and have the
            transformation applied before being returned.
        """
        return self._children

    @property  # read-only via getter-only and read-only return type `Sequence`
    def raw_children(self) -> Sequence[NodeType]:
        """Return all the raw children of this node (i.e. without being copied or
        transformed).
        """
        return self._children

    def get_flattened_nodes(self) -> Sequence[Node]:
        """Get the ultimate descendant nodes.

        This method recursively traverses the node hierarchy, yielding only the final
        descendant nodes (the nodes that have no further children, like the leaves of a
        tree).

        Note:
            Nodes that are children of a transformation node (such as
            :py:class:`Rotation` or :py:class:`Translation`) are copied and have the
            transformation applied before being returned.

        Returns:
            All ultimate descendant nodes.
        """
        nodes: list[Node] = []
        for child in self.children:
            nodes += child.get_flattened_nodes()
        return nodes

    def translate(self, vector: Vector2D) -> Self:
        """Move all the child nodes.

        Args:
            vector: The distance in mm in the x- and y-direction.

        Returns:
            Itself after translating all the child nodes (in place).
        """
        for child in self.children:
            child.translate(vector)
        return self

    def rotate(
        self,
        angle: float,
        origin: Vector2D = Vector2D.zero(),
    ) -> Self:
        """Rotate all the child nodes around a given point.

        Args:
            angle: Rotation angle in degrees.
            origin: Coordinates (in mm) of the point around which to rotate.

        Returns:
            Itself after rotating all child nodes (in place).
        """
        for child in self._children:
            child.rotate(angle, origin)
        return self

    @staticmethod
    def _remove_node(*, parent: Container[NodeType], node: NodeType) -> None:
        """Remove a child from the list of child nodes of a given parent node.

        Args:
            parent: The parent node.
            node: The node to remove.
        """
        while node in parent._children:
            parent._children.remove(node)
            node._parent = None

    def __iter__(self) -> Iterator[NodeType]:
        """Return an iterator to iterate through all child nodes of this object.

        Note:
            Nodes that are children of a transformation node (such as
            :py:class:`Rotation` or :py:class:`Translation`) are copied and have the
            transformation applied before being returned.
        """
        return iter(self.children)

    def __len__(self) -> int:
        """Return the number of children this node has."""
        return len(self._children)

    def __add__(self, nodes: NodeType | Iterable[NodeType]) -> Self:
        """Convenience function to allow simple append/extend to a Node."""
        if isinstance(nodes, Node):
            self.append(nodes)
        else:
            self.extend(nodes)
        return self
