import gradio as gr

from dotenv import load_dotenv
from mcp_client_wrapper import MCPClientWrapper

load_dotenv(dotenv_path=".env")

mcp_client = MCPClientWrapper()

def gradio_interface():
    with gr.Blocks(title="MCP Client") as demo:
        gr.Markdown("# MCP Assistant")
        gr.Markdown("Connect to your MCP server and chat with the assistant")
        
        with gr.Row(equal_height=True):
            with gr.Column(scale=4):
                server_url = gr.Textbox(
                    label="Endpoint of the MCP server",
                    placeholder="Enter the server URL (e.g., http://localhost:8000/sse)",
                    value="http://localhost:8000/sse"
                )
                
                status = gr.Textbox(label="Connection Status", interactive=False)
            with gr.Column(scale=1):
                connect_btn = gr.Button("Connect")
        
        chatbot = gr.Chatbot(
            value=[], 
            height=500,
            type="messages",
            show_copy_button=True,
            avatar_images=("👤", "🤖")
        )
        
        with gr.Row(equal_height=True):
            msg = gr.Textbox(
                label="Your Question",
                placeholder="Talk to the assistant...",
                scale=4
            )
            clear_btn = gr.Button("Clear Chat", scale=1)
        
        connect_btn.click(mcp_client.connect, inputs=server_url, outputs=status)
        msg.submit(mcp_client.process_message, [msg, chatbot], [chatbot, msg])
        clear_btn.click(lambda: [], None, chatbot)
        
    return demo

if __name__ == "__main__":
    interface = gradio_interface()
    interface.launch(debug=True)