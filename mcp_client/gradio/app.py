import gradio as gr

from dotenv import load_dotenv
from mcp_client_wrapper import MCPClientWrapper

load_dotenv(dotenv_path=".env")

mcp_client = MCPClientWrapper()

def on_user_change(user: str) -> gr.Chatbot:
    messages = mcp_client.load_user_messages(user)
    return gr.Chatbot(value=messages, height=300, type="messages")

def gradio_interface():
    with gr.Blocks(title="MCP Client") as demo:
        gr.Markdown("# MCP Assistant")
        gr.Markdown("Connect to your MCP server and chat with the assistant")

        dropdown_user = gr.Dropdown(choices=["Mark", "Michelle", "John"], label="Select the user", value="Mark")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=4):
                server_url = gr.Textbox(
                    label="Endpoint of the MCP server",
                    placeholder="Enter the server URL (e.g., http://localhost:8000/sse)",
                    value=""
                )

            with gr.Column(scale=1):
                connect_btn = gr.Button("Connect", variant="primary")
            
        mcp_tools = gr.Textbox(label="MCP tools", interactive=False, max_lines=5)
        
        chatbot = gr.Chatbot(
            value=mcp_client.load_user_messages(dropdown_user.value), 
            height=300,
            type="messages"
        )

        dropdown_user.change(on_user_change, inputs=dropdown_user, outputs=chatbot)
        
        with gr.Row(equal_height=True):
            msg = gr.Textbox(
                label="Your message",
                placeholder="Talk to the assistant...",
                scale=4
            )
        
        connect_btn.click(mcp_client.connect, inputs=[server_url, mcp_tools], outputs=mcp_tools)
        msg.submit(mcp_client.process_message, [msg, chatbot, dropdown_user], [chatbot, msg])
        
    return demo


interface = gradio_interface()
interface.launch()