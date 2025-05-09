import gradio as gr

from dotenv import load_dotenv
from mcp_client_wrapper import MCPClientWrapper

load_dotenv(dotenv_path=".env")

mcp_client = MCPClientWrapper()

def on_user_change(user: str) -> gr.Chatbot:
    messages = mcp_client.load_user_messages(user)
    return gr.Chatbot(value=messages, height=500, type="messages")

def gradio_interface():
    with gr.Blocks(title="MCP Client") as demo:

        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                gr.Markdown("## MCP Client")
                gr.Markdown("Connect to your MCP server and chat with the assistant")

            with gr.Column(scale=5):
                dropdown_user = gr.Dropdown(choices=["Mark", "Michelle", "John"], label="Select the user", value="Mark")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=5):
                server_url = gr.Textbox(
                    label="Endpoint of the MCP server",
                    placeholder="Enter the server URL (e.g., http://localhost:8000/sse)",
                    value=""
                )

                connect_btn = gr.Button("Connect", variant="primary")
            
            with gr.Column(scale=5):
                mcp_tools = gr.Textbox(label="MCP tools", interactive=False, max_lines=3)
        
        chatbot = gr.Chatbot(
            value=mcp_client.load_user_messages(dropdown_user.value), 
            height=500,
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
interface.launch(server_port=8000)