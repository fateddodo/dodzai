"""Tkinter desktop application for DodzAI."""
from __future__ import annotations

import os
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
from tkinter.scrolledtext import ScrolledText
from typing import Optional

from ..engine import DodzAIEngine
from ..models import MessageRole
from ..utils.markdown import parse_markdown


class DodzAIApp(tk.Tk):
    """Tkinter based desktop application that wraps :class:`DodzAIEngine`."""

    def __init__(self, engine: Optional[DodzAIEngine] = None) -> None:
        super().__init__()
        self.title("DodzAI")
        self.geometry("1100x720")
        self.minsize(900, 600)

        self.engine = engine or DodzAIEngine()
        self.current_provider = None
        self.current_model = None

        self._configure_styles()
        self._build_layout()
        self._ensure_authenticated()
        self._load_providers()
        self._refresh_conversations()

    # ------------------------------------------------------------------
    def _configure_styles(self) -> None:
        style = ttk.Style(self)
        theme = "clam"
        if theme in style.theme_names():
            style.theme_use(theme)
        style.configure("DodzAI.TFrame", padding=10)
        style.configure("DodzAI.Header.TLabel", font=("Segoe UI", 14, "bold"))
        style.configure("DodzAI.TButton", padding=6)

    def _build_layout(self) -> None:
        container = ttk.Frame(self, style="DodzAI.TFrame")
        container.pack(fill=tk.BOTH, expand=True)

        self.columnconfigure(0, weight=1)
        container.columnconfigure(0, weight=1)
        container.columnconfigure(1, weight=3)
        container.rowconfigure(0, weight=1)
        container.rowconfigure(1, weight=0)

        # Sidebar for conversations and provider selection
        sidebar = ttk.Frame(container)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 12))
        sidebar.columnconfigure(0, weight=1)

        ttk.Label(sidebar, text="Conversations", style="DodzAI.Header.TLabel").grid(row=0, column=0, sticky="w")
        self.conversation_listbox = tk.Listbox(sidebar, exportselection=False, height=18)
        self.conversation_listbox.grid(row=1, column=0, sticky="nsew", pady=(6, 12))
        self.conversation_listbox.bind("<<ListboxSelect>>", self._on_conversation_select)

        provider_frame = ttk.Frame(sidebar)
        provider_frame.grid(row=2, column=0, sticky="ew")
        provider_frame.columnconfigure(1, weight=1)
        ttk.Label(provider_frame, text="Provider").grid(row=0, column=0, sticky="w")
        self.provider_combo = ttk.Combobox(provider_frame, state="readonly")
        self.provider_combo.grid(row=0, column=1, sticky="ew")
        self.provider_combo.bind("<<ComboboxSelected>>", self._on_provider_changed)

        ttk.Label(provider_frame, text="Model").grid(row=1, column=0, sticky="w", pady=(6, 0))
        self.model_combo = ttk.Combobox(provider_frame, state="readonly")
        self.model_combo.grid(row=1, column=1, sticky="ew", pady=(6, 0))

        ttk.Button(sidebar, text="New Chat", command=self._start_conversation, style="DodzAI.TButton").grid(
            row=3, column=0, sticky="ew", pady=(12, 0)
        )

        # Chat area ------------------------------------------------------
        chat_frame = ttk.Frame(container)
        chat_frame.grid(row=0, column=1, sticky="nsew")
        chat_frame.columnconfigure(0, weight=1)
        chat_frame.rowconfigure(0, weight=1)

        self.chat_display = ScrolledText(chat_frame, wrap=tk.WORD, height=20)
        self.chat_display.grid(row=0, column=0, sticky="nsew")
        self.chat_display.configure(state=tk.DISABLED)
        self._configure_chat_tags()

        input_frame = ttk.Frame(chat_frame)
        input_frame.grid(row=1, column=0, sticky="ew", pady=(12, 0))
        input_frame.columnconfigure(0, weight=1)

        self.message_entry = tk.Text(input_frame, height=4, wrap=tk.WORD)
        self.message_entry.grid(row=0, column=0, sticky="ew")

        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=0, column=1, sticky="nsw", padx=(8, 0))
        ttk.Button(button_frame, text="Send", command=self._send_message, style="DodzAI.TButton").grid(row=0, column=0, pady=2)
        ttk.Button(button_frame, text="Generate Image", command=self._generate_image).grid(row=1, column=0, pady=2)
        ttk.Button(button_frame, text="Analyze Image", command=self._analyze_image).grid(row=2, column=0, pady=2)
        ttk.Button(button_frame, text="Speak Reply", command=self._speak_reply).grid(row=3, column=0, pady=2)

        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(container, textvariable=self.status_var, anchor="w")
        status_bar.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(12, 0))

    def _configure_chat_tags(self) -> None:
        self.chat_display.tag_configure("user", foreground="#2c7be5", font=("Consolas", 11, "bold"))
        self.chat_display.tag_configure("assistant", foreground="#1f1f1f", font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("paragraph", font=("Segoe UI", 11))
        self.chat_display.tag_configure("header1", font=("Segoe UI", 14, "bold"))
        self.chat_display.tag_configure("header2", font=("Segoe UI", 12, "bold"))
        self.chat_display.tag_configure("list_item", font=("Segoe UI", 11))
        self.chat_display.tag_configure("code", font=("Consolas", 11), background="#f2f2f2")
        self.chat_display.tag_configure("code_block", font=("Consolas", 11), background="#f7f7f7", lmargin1=20, lmargin2=20)
        self.chat_display.tag_configure("bold", font=("Segoe UI", 11, "bold"))
        self.chat_display.tag_configure("italic", font=("Segoe UI", 11, "italic"))

    # ------------------------------------------------------------------
    def _ensure_authenticated(self) -> None:
        username = os.getenv("DODZAI_USERNAME", "demo")
        password = os.getenv("DODZAI_PASSWORD", "demo")
        if not self.engine.login(username, password, create=True):
            messagebox.showerror("Authentication Failed", "Unable to authenticate with the local profile store.")
        else:
            self.status_var.set(f"Logged in as {username}")

    def _load_providers(self) -> None:
        providers = self.engine.providers()
        self.provider_combo["values"] = providers
        if providers:
            self.provider_combo.current(0)
            self._on_provider_changed()

    def _refresh_conversations(self) -> None:
        self.conversation_listbox.delete(0, tk.END)
        for conversation in self.engine.conversation_list():
            label = f"{conversation.title} ({conversation.provider})"
            self.conversation_listbox.insert(tk.END, label)
        if self.conversation_listbox.size() > 0:
            self.conversation_listbox.select_set(0)
            self._on_conversation_select(None)

    def _select_conversation(self, identifier: str) -> None:
        conversations = self.engine.conversation_list()
        for index, conversation in enumerate(conversations):
            if conversation.identifier == identifier:
                self.conversation_listbox.select_clear(0, tk.END)
                self.conversation_listbox.select_set(index)
                self.conversation_listbox.see(index)
                self._display_conversation(conversation)
                return

    # ------------------------------------------------------------------
    def _on_provider_changed(self, *_args) -> None:
        provider = self.provider_combo.get()
        if not provider:
            return
        self.current_provider = provider
        models = [m for m in self.engine.models(provider)]
        self.model_combo["values"] = models
        if models:
            self.model_combo.current(0)
            self.current_model = models[0]

    def _on_conversation_select(self, event) -> None:
        selection = self.conversation_listbox.curselection()
        if not selection:
            return
        index = selection[0]
        conversation = self.engine.conversation_list()[index]
        self._display_conversation(conversation)

    def _display_conversation(self, conversation) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.delete("1.0", tk.END)
        for message in conversation.messages:
            role_tag = "user" if message.role == MessageRole.USER else "assistant"
            self.chat_display.insert(tk.END, ("You" if role_tag == "user" else "Assistant") + ":\n", role_tag)
            self._insert_markdown(message.content)
            self.chat_display.insert(tk.END, "\n\n")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)

    def _insert_markdown(self, content: str) -> None:
        segments = parse_markdown(content)
        for segment in segments:
            if segment.style == "code_block":
                self.chat_display.insert(tk.END, segment.text + "\n", "code_block")
            else:
                self._insert_inline(segment.text, segment.style)
                self.chat_display.insert(tk.END, "\n")

    def _insert_inline(self, text: str, style: str) -> None:
        import re

        pattern = re.compile(r"<(bold|italic|code)>(.*?)</\\1>")
        position = 0
        for match in pattern.finditer(text):
            if match.start() > position:
                self.chat_display.insert(tk.END, text[position : match.start()], style)
            tag = match.group(1)
            self.chat_display.insert(tk.END, match.group(2), tag)
            position = match.end()
        if position < len(text):
            self.chat_display.insert(tk.END, text[position:], style)

    # ------------------------------------------------------------------
    def _start_conversation(self) -> None:
        provider = self.provider_combo.get()
        if not provider:
            messagebox.showinfo("Select Provider", "Please choose a provider before starting a chat.")
            return
        conversation = self.engine.start_conversation(provider, title="New Chat")
        self.status_var.set(f"Started conversation with {provider}")
        self._refresh_conversations()
        self._select_conversation(conversation.identifier)

    def _send_message(self) -> None:
        content = self.message_entry.get("1.0", tk.END).strip()
        if not content:
            return
        provider = self.provider_combo.get()
        if not provider:
            messagebox.showinfo("Select Provider", "Please choose a provider before sending a message.")
            return
        model = self.model_combo.get()
        _ = self.engine.send_message(provider, content, model=model)
        self.message_entry.delete("1.0", tk.END)
        self.status_var.set("Message sent")
        active_id = self.engine.conversations.active_id
        self._refresh_conversations()
        if active_id:
            self._select_conversation(active_id)

    def _generate_image(self) -> None:
        provider = self.provider_combo.get()
        if not provider:
            return
        prompt = simpledialog.askstring("Image Prompt", "Describe the image you want to generate:")
        if not prompt:
            return
        path = self.engine.generate_image(provider, prompt)
        if path:
            self.status_var.set(f"Image generated at {path}")
        else:
            self.status_var.set("Image generation failed")

    def _analyze_image(self) -> None:
        provider = self.provider_combo.get()
        if not provider:
            return
        image_path = filedialog.askopenfilename(title="Select image for analysis")
        if not image_path:
            return
        prompt = simpledialog.askstring("Vision Prompt", "Describe what you want to know about the image:")
        response = self.engine.analyze_image(provider, prompt or "Analyze this image", image_path)
        self._append_response(response.message.content)

    def _speak_reply(self) -> None:
        provider = self.provider_combo.get()
        if not provider:
            return
        conversation = self.engine.conversation_list()
        if not conversation:
            return
        last = conversation[-1].messages[-1]
        self.engine.text_to_speech(last.content)
        self.status_var.set("Reply spoken (or saved to file)")

    def _append_response(self, content: str) -> None:
        self.chat_display.configure(state=tk.NORMAL)
        self.chat_display.insert(tk.END, "Assistant:\n", "assistant")
        self._insert_markdown(content)
        self.chat_display.insert(tk.END, "\n")
        self.chat_display.configure(state=tk.DISABLED)
        self.chat_display.see(tk.END)


def launch() -> None:
    app = DodzAIApp()
    app.mainloop()
