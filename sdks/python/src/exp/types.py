from collections.abc import Callable
from typing import Annotated, Any, Generic, Literal, TypeAlias, TypeVar

from pydantic import BaseModel, ConfigDict, Field, RootModel
from pydantic.networks import AnyUrl, UrlConstraints


"""
Model Context Protocol bindings for Python

These bindings were generated from https://github.com/modelcontextprotocol/specification,
using Claude, with a prompt something like the following:

Generate idiomatic Python bindings for this schema for MCP, or the "Model Context
Protocol." The schema is defined in TypeScript, but there's also a JSON Schema version
for reference.

* For the bindings, let's use Pydantic V2 models.
* Each model should allow extra fields everywhere, by specifying `model_config =
  ConfigDict(extra='allow')`. Do this in every case, instead of a custom base class.
* Union types should be represented with a Pydantic `RootModel`.
* Define additional model classes instead of using dictionaries. Do this even if they're
  not separate types in the schema.
"""

Role = Literal["user", "assistant"]
RequestId = Annotated[int, Field(strict=True)] | str
AnyFunction: TypeAlias = Callable[..., Any]


class RequestParams(BaseModel):
    pass


RequestParamsT = TypeVar(
    "RequestParamsT", bound=RequestParams | dict[str, Any] | None)
MethodT = TypeVar("MethodT", bound=str)


class Request(BaseModel, Generic[RequestParamsT, MethodT]):
    """Base class for JSON-RPC requests."""

    method: MethodT
    params: RequestParamsT
    model_config = ConfigDict(extra="allow")


class Result(BaseModel):
    """Base class for JSON-RPC results."""

    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """
    model_config = ConfigDict(extra="allow")


class JSONRPCRequest(Request[dict[str, Any] | None, str]):
    """A request that expects a response."""

    jsonrpc: Literal["2.0"]
    id: RequestId
    method: str
    params: dict[str, Any] | None = None


class JSONRPCResponse(BaseModel):
    """A successful (non-error) response to a request."""

    jsonrpc: Literal["2.0"]
    id: RequestId
    result: dict[str, Any]
    model_config = ConfigDict(extra="allow")


# SDK error codes
CONNECTION_CLOSED = -32000
# REQUEST_TIMEOUT = -32001  # the typescript sdk uses this

# Standard JSON-RPC error codes
PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603


class ErrorData(BaseModel):
    """Error information for JSON-RPC error responses."""

    code: int
    """The error type that occurred."""

    message: str
    """
    A short description of the error. The message SHOULD be limited to a concise single
    sentence.
    """

    data: Any | None = None
    """
    Additional information about the error. The value of this member is defined by the
    sender (e.g. detailed error information, nested errors etc.).
    """

    model_config = ConfigDict(extra="allow")


class JSONRPCError(BaseModel):
    """A response to a request that indicates an error occurred."""

    jsonrpc: Literal["2.0"]
    id: str | int
    error: ErrorData
    model_config = ConfigDict(extra="allow")


class JSONRPCMessage(RootModel[JSONRPCRequest | JSONRPCResponse | JSONRPCError]):
    pass


class EmptyResult(Result):
    """A response that indicates success but carries no data."""


class BaseMetadata(BaseModel):
    """Base class for entities with name and optional title fields."""

    name: str | None = None
    """The programmatic name of the entity."""

    title: str | None = None
    """
    Intended for UI and end-user contexts — optimized to be human-readable and easily understood,
    even by those unfamiliar with domain-specific terminology.

    If not provided, the name should be used for display (except for Function,
    where `annotations.title` should be given precedence over using `name`,
    if present).
    """


class Annotations(BaseModel):
    audience: list[Role] | None = None
    priority: Annotated[float, Field(ge=0.0, le=1.0)] | None = None
    model_config = ConfigDict(extra="allow")


class ResourceContents(BaseModel):
    """The contents of a specific resource or sub-resource."""

    uri: Annotated[AnyUrl, UrlConstraints(host_required=False)]
    """The URI of this resource."""
    mimeType: str | None = None
    """The MIME type of this resource, if known."""
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """
    model_config = ConfigDict(extra="allow")


class TextResourceContents(ResourceContents):
    """Text contents of a resource."""

    text: str
    """
    The text of the item. This must only be set if the item can actually be represented
    as text (not binary data).
    """


class BlobResourceContents(ResourceContents):
    """Binary contents of a resource."""

    blob: str
    """A base64-encoded string representing the binary data of the item."""


class TextContent(BaseModel):
    """Text content for a message."""

    type: Literal["text"]
    text: str
    """The text content of the message."""
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """
    model_config = ConfigDict(extra="allow")


class ImageContent(BaseModel):
    """Image content for a message."""

    type: Literal["image"]
    data: str
    """The base64-encoded image data."""
    mimeType: str
    """
    The MIME type of the image. Different providers may support different
    image types.
    """
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """
    model_config = ConfigDict(extra="allow")


class AudioContent(BaseModel):
    """Audio content for a message."""

    type: Literal["audio"]
    data: str
    """The base64-encoded audio data."""
    mimeType: str
    """
    The MIME type of the audio. Different providers may support different
    audio types.
    """
    annotations: Annotations | None = None
    meta: dict[str, Any] | None = Field(alias="_meta", default=None)
    """
    See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
    for notes on _meta usage.
    """
    model_config = ConfigDict(extra="allow")


ContentBlock = TextContent | ImageContent | AudioContent
"""A content block that can be used in prompts and function results."""

Content: TypeAlias = ContentBlock
# """DEPRECATED: Content is deprecated, you should use ContentBlock directly."""


class ListFunctionsRequest(Request[None, Literal["functions/list"]]):
    """Sent from the client to request a list of functions the server has."""

    method: Literal["functions/list"] = "functions/list"


class InitializeRequestParams(RequestParams):
    pass


class InitializeRequest(Request[InitializeRequestParams, Literal["initialize"]]):
    """
    This request is sent from the client to the server when it first connects, asking it
    to begin initialization.
    """
    method: Literal["initialize"] = "initialize"


class FunctionT(BaseMetadata):

    name: str
    """Definition for a function the client can call."""
    description: str | None = None
    """A human-readable description of the function."""
    inputSchema: dict[str, Any]
    """A JSON Schema object defining the expected parameters for the function."""
    outputSchema: dict[str, Any] | None = None
    """
    An optional JSON Schema object defining the structure of the function's output
    returned in the structuredContent field of a CallFunctionResult.
    """
    model_config = ConfigDict(extra="allow")


class ServerCapabilities(BaseModel):
    """Capabilities that a server may support."""

    functions:  dict[str, FunctionT]
    """Present if the server offers any functions to call."""

    classes: dict[str, Any]
    model_config = ConfigDict(extra="allow")


class InitializeResult(Result):
    """The version of the Model Context Protocol that the server wants to use."""
    capabilities: ServerCapabilities


class ListFunctionsResult(Result):
    """The server's response to a functions/list request from the client."""
    functions: list[FunctionT]


class CallFunctionRequestParams(RequestParams):
    """Parameters for calling a function."""

    name: str
    arguments: dict[str, Any] | None = None
    model_config = ConfigDict(extra="allow")


class CallFunctionRequest(Request[CallFunctionRequestParams, Literal["functions/call"]]):
    """Used by the client to invoke a function provided by the server."""

    method: Literal["functions/call"] = "functions/call"
    params: CallFunctionRequestParams


class CallFunctionResult(Result):
    """The server's response to a function call."""

    content: list[ContentBlock]
    structuredResult: dict[str, Any] | None = None
    """An optional JSON object that represents the structured result of the function call."""
    isError: bool = False


LoggingLevel = Literal["debug", "info", "notice",
                       "warning", "error", "critical", "alert", "emergency"]


IncludeContext = Literal["none", "thisServer", "allServers"]


StopReason = Literal["endTurn", "stopSequence", "maxTokens"] | str


class ClientRequest(
    RootModel[
        InitializeRequest
        | CallFunctionRequest
        | ListFunctionsRequest
    ]
):
    pass


class ServerResult(
    RootModel[
        EmptyResult
        | InitializeResult
        | CallFunctionResult
        | ListFunctionsResult
    ]
):
    pass
