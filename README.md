# DrawGen: AI-Powered Diagram Generator

 <!-- TODO: Replace with an actual screenshot or GIF of the app -->

**DrawGen** is a real-time, conversational diagramming tool. Describe your architecture, flowchart, or network topology in plain language, and watch it come to life instantly. It uses a powerful Large Language Model (LLM) backend to generate and modify [draw.io](https://draw.io) diagrams through a simple chat interface.


---

## ✨ Features

- **Conversational Interface:** Build and refine diagrams through a simple chat. No drag-and-drop required.
- **Real-Time Updates:** See your changes reflected instantly in the live draw.io editor.
- **Stateful Conversations:** The AI remembers the context of your diagram, allowing for complex, iterative modifications.
- **Robust Response Handling:** Gracefully handles both diagram (XML) and text-based (clarifications, questions) responses from the AI.
- **Error Logging:** Automatically captures both client-side and server-side errors into a `feedback.md` file for easy debugging.
- **Simple & Lightweight:** A single-page application with a clean Python/FastAPI backend. No database required.

---

## 🚀 How It Works

1.  **User Prompt:** The user enters a prompt in the chat interface (e.g., "Create a simple web server architecture").
2.  **WebSocket Communication:** The prompt is sent to the FastAPI backend via a WebSocket connection.
3.  **AI-Powered Generation:** The backend sends the entire conversation history to an LLM API (like DeepSeek), instructing it to return a `mxGraphModel` XML string.
4.  **Response Handling:**
    - If the AI returns valid XML, it's sent back to the client.
    - If the AI returns a text message (e.g., "Can you clarify what you mean by 'core'?"), it's sent as a chat message.
5.  **Live Update:** The frontend receives the message and uses the `postMessage` API to load the XML into the embedded draw.io iframe, instantly updating the diagram.

---

## 🛠️ Technology Stack

- **Backend:** Python, FastAPI, Uvicorn
- **AI Integration:** `httpx` for asynchronous API calls
- **Real-time:** WebSockets
- **Frontend:** Vanilla HTML, CSS, and JavaScript
- **Diagramming:** draw.io (diagrams.net) Embedded API

---

## 📋 Requirements

- Python 3.9+
- An API Key from an LLM provider (e.g., DeepSeek, OpenAI) or a running local Ollama instance.

---

## ⚙️ Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/drawgen.git
    cd drawgen
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    # Windows
    python -m venv venv
    .\venv\Scripts\Activate.ps1

    # macOS / Linux
    python3 -m venv venv
    source venv/bin/activate
    ```

3.  **Install the dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

---

## ⚙️ Configuration

The application is configured via a `.env` file.

1.  **Create your `.env` file** by copying the example file:
    ```bash
    cp .env.example .env
    ```

2.  **Edit the `.env` file** to choose your provider and add the necessary credentials.

    -   **Set the Provider:** Choose between `deepseek`, `openai`, or `ollama`.
        ```ini
        LLM_PROVIDER=deepseek
        ```

    -   **Add Keys & Models:** Fill in the details for your chosen provider (e.g., `DEEPSEEK_API_KEY` for DeepSeek, `OLLAMA_MODEL` for Ollama, etc.). Refer to the comments in the `.env.example` file for guidance.

---

## ▶️ Running the Application

1.  **Start the server:**
    ```bash
    uvicorn app:app --reload
    ```

2.  **Open your browser:**
    Navigate to `http://localhost:8000`. You should see the DrawGen interface ready to go!

---

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

---

## 👤 Author

- **Designed by Eiji**

---

## 📄 License

This project is licensed under the MIT License. See the `LICENSE` file for details.

