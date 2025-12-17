import { z } from "zod";


/* JSON-RPC types */
export const JSONRPC_VERSION = "2.0";


/**
 * A uniquely identifying ID for a request in JSON-RPC.
 */
export const RequestIdSchema = z.union([z.string(), z.number().int()]);


export const RequestSchema = z.object({
  method: z.string(),
  params : z.record(z.string() , z.any()),
});

export const ResultSchema = z
  .object({
    _meta: z.optional(z.object({}).passthrough()),
  })
  .passthrough();

/**
 * A request that expects a response.
 */
export const JSONRPCRequestSchema = z
  .object({
    jsonrpc: z.literal(JSONRPC_VERSION),
    id: RequestIdSchema,
  })
  .merge(RequestSchema)
  .strict();

/**
 * A successful (non-error) response to a request.
 */
export const JSONRPCResponseSchema = z
  .object({
    jsonrpc: z.literal(JSONRPC_VERSION),
    id: RequestIdSchema,
    result: ResultSchema,
  })
  .strict();


/**
 * A response to a request that indicates an error occurred.
 */
export const JSONRPCErrorSchema = z
  .object({
    jsonrpc: z.literal(JSONRPC_VERSION),
    id: RequestIdSchema,
    error: z.object({
      /**
       * The error type that occurred.
       */
      code: z.number().int(),
      /**
       * A short description of the error. The message SHOULD be limited to a concise single sentence.
       */
      message: z.string(),
      /**
       * Additional information about the error. The value of this member is defined by the sender (e.g. detailed error information, nested errors etc.).
       */
      data: z.optional(z.unknown()),
    }),
  })
  .strict();


export const JSONRPCMessageSchema = z.union([
  JSONRPCRequestSchema,
  JSONRPCResponseSchema,
  JSONRPCErrorSchema
]);

/**
 * Error codes defined by the JSON-RPC specification.
 */
export enum ErrorCode {
  // SDK error codes
  ConnectionClosed = -32000,
  RequestTimeout = -32001,

  // Standard JSON-RPC error codes
  ParseError = -32700,
  InvalidRequest = -32600,
  MethodNotFound = -32601,
  InvalidParams = -32602,
  InternalError = -32603,
}


export class McpError extends Error {
  constructor(
    public readonly code: number,
    message: string,
    public readonly data?: unknown,
  ) {
    super(`MCP error ${code}: ${message}`);
    this.name = "McpError";
  }
}


export const isJSONRPCRequest = (value: unknown): value is JSONRPCRequest =>
  JSONRPCRequestSchema.safeParse(value).success;
export const isJSONRPCResponse = (value: unknown): value is JSONRPCResponse =>
  JSONRPCResponseSchema.safeParse(value).success;
export const isJSONRPCError = (value: unknown): value is JSONRPCError =>
  JSONRPCErrorSchema.safeParse(value).success;

  

export type JSONRPCMessage = z.infer<typeof JSONRPCMessageSchema>;
export type JSONRPCResponse = z.infer<typeof JSONRPCResponseSchema>;
export type JSONRPCRequest = z.infer<typeof JSONRPCRequestSchema>;
export type JSONRPCError = z.infer<typeof JSONRPCErrorSchema>;

export type Request = z.infer<typeof RequestSchema>;
export type Result = z.infer<typeof ResultSchema>;
export type RequestId = z.infer<typeof RequestIdSchema>;



/**
 * A Zod schema for validating Base64 strings that is more performant and
 * robust for very large inputs than the default regex-based check. It avoids
 * stack overflows by using the native `atob` function for validation.
 */
const Base64Schema = z.string().refine(
    (val) => {
        try {
            // atob throws a DOMException if the string contains characters
            // that are not part of the Base64 character set.
            atob(val);
            return true;
        } catch {
            return false;
        }
    },
    { message: "Invalid Base64 string" },
);




/**
 * Text provided to or from an LLM.
 */
export const TextContentSchema = z
  .object({
    type: z.literal("text"),
    /**
     * The text content of the message.
     */
    text: z.string(),

    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: z.optional(z.object({}).passthrough()),
  })
  .passthrough();

/**
 * An image provided to or from an LLM.
 */
export const ImageContentSchema = z
  .object({
    type: z.literal("image"),
    /**
     * The base64-encoded image data.
     */
    data: Base64Schema,
    /**
     * The MIME type of the image. Different providers may support different image types.
     */
    mimeType: z.string(),

    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: z.optional(z.object({}).passthrough()),
  })
  .passthrough();

/**
 * An Audio provided to or from an LLM.
 */
export const AudioContentSchema = z
  .object({
    type: z.literal("audio"),
    /**
     * The base64-encoded audio data.
     */
    data: Base64Schema,
    /**
     * The MIME type of the audio. Different providers may support different audio types.
     */
    mimeType: z.string(),

    /**
     * See [MCP specification](https://github.com/modelcontextprotocol/modelcontextprotocol/blob/47339c03c143bb4ec01a26e721a1b8fe66634ebe/docs/specification/draft/basic/index.mdx#general-fields)
     * for notes on _meta usage.
     */
    _meta: z.optional(z.object({}).passthrough()),
  })
  .passthrough();

/**
 * A content block that can be used in prompts and tool results.
 */
export const ContentBlockSchema = z.union([
  TextContentSchema,
  ImageContentSchema,
  AudioContentSchema,
]);


/**
 * The server's response to a tool call.  CallFunctionResultSchema
 */
export const CallFunctionResultSchema = ResultSchema.extend({
  /**
   * A list of content objects that represent the result of the tool call.
   *
   * If the Tool does not define an outputSchema, this field MUST be present in the result.
   * For backwards compatibility, this field is always present, but it may be empty.
   */
  content: z.array(ContentBlockSchema).default([]),

  /**
   * An object containing structured tool output.
   *
   * If the Tool defines an outputSchema, this field MUST be present in the result, and contain a JSON object that matches the schema.
   */
  structuredResult: z.any().optional(),
  
  /**
   * Whether the tool call ended in an error.
   *
   * If not set, this is assumed to be false (the call was successful).
   *
   * Any errors that originate from the tool SHOULD be reported inside the result
   * object, with `isError` set to true, _not_ as an MCP protocol-level error
   * response. Otherwise, the LLM would not be able to see that an error occurred
   * and self-correct.
   *
   * However, any errors in _finding_ the tool, an error indicating that the
   * server does not support tool calls, or any other exceptional conditions,
   * should be reported as an MCP error response.
   */
  isError: z.optional(z.boolean()),
});


/**
 * CallToolResultSchema extended with backwards compatibility to protocol version 2024-10-07.
 */
export const CompatibilityCallToolResultSchema = CallFunctionResultSchema.or(
  ResultSchema.extend({
    toolResult: z.unknown(),
  }),
);


/* functions */
/**
 * Used by the client to invoke a tool provided by the server.
 */

/**
 * A progress token, used to associate progress notifications with the original request.
 */
export const ProgressTokenSchema = z.union([z.string(), z.number().int()]);


const RequestMetaSchema = z
  .object({
    /**
     * If specified, the caller is requesting out-of-band progress notifications for this request (as represented by notifications/progress). The value of this parameter is an opaque token that will be attached to any subsequent notifications. The receiver is not obligated to provide these notifications.
     */
    progressToken: z.optional(ProgressTokenSchema),
  })
  .passthrough();

const BaseRequestParamsSchema = z
  .object({
    _meta: z.optional(RequestMetaSchema),
  })
  .passthrough();


/**
 * Used by the client to invoke a tool provided by the server.
 */
export const CallFunctionRequestSchema = RequestSchema.extend({
  method: z.literal("functions/call"),
  params: z.object({
    name: z.string(),
    arguments: z.optional(z.record(z.string(), z.unknown()))
  }),
});

export type CallFunctionRequest = z.infer<typeof CallFunctionRequestSchema>;
export type CallFunctionResult = z.infer<typeof CallFunctionResultSchema>;

/**
 * Assert 'object' type schema.
 *
 * @internal
 */
const AssertObjectSchema = z.custom<object>((v): v is object => v !== null && (typeof v === 'object' || typeof v === 'function'));



export const FunctionSchema = z.object({
    name: z.string(),
    inputSchema: z
        .object({
            type: z.literal('object'),
            properties: z.record(z.string(), AssertObjectSchema).optional(),
            required: z.array(z.string()).optional()
        })
        .catchall(z.unknown()),
    outputSchema: z
        .object({
            type: z.literal('object'),
            properties: z.record(z.string(), AssertObjectSchema).optional(),
            required: z.array(z.string()).optional()
        })
        .catchall(z.unknown())
        .optional(),
});

/**
 * Capabilities that a server may support. Known capabilities are defined here, in this schema, but this is not a closed set: any server can define its own, additional capabilities.
 */
export const ServerCapabilitiesSchema = z.object({
  /**
   * list of  the server function calls and class class . 
   */
  functions : z.record(z.string() ,FunctionSchema),
  classes : z.record(z.string() , z.any())
})


/**
 * After receiving an initialize request from the client, the server sends this response.
*/
export const InitializeResultSchema = ResultSchema.extend({
 capabilities: ServerCapabilitiesSchema,
});


export const InitializeRequestSchema = RequestSchema.extend({
  method:z.literal("initialize"),
})

export type ServerCapabilities = z.infer<typeof ServerCapabilitiesSchema>;
export type InitializeResult = z.infer<typeof InitializeResultSchema>;
export type InitializeRequest = z.infer<typeof InitializeRequestSchema>;


/**
 * Sent from the client to request a list of tools the server has.
 */
export const ListFunctionsRequestSchema = RequestSchema.extend({
  method: z.literal("functions/list"),
});

/**
 * The server's response to a tools/list request from the client.
 */
export const ListFunctionsResultSchema = ResultSchema.extend({
  functions: z.array(FunctionSchema),
});

export type FunctionT = z.infer<typeof FunctionSchema>;
export type ListFunctionsResult = z.infer<typeof ListFunctionsResultSchema>;
export type ListFunctionsRequest = z.infer<typeof ListFunctionsRequestSchema>;