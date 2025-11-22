import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function fetchTasks() {
  const response = await fetch(`${API_URL}/tasks/`);
  if (!response.ok) {
    throw new Error("Failed to fetch tasks");
  }
  return response.json();
}

async function createTask(payload) {
  const response = await fetch(`${API_URL}/tasks/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!response.ok) {
    throw new Error("Failed to create task");
  }
  return response.json();
}

function TaskList() {
  const queryClient = useQueryClient();
  const { data: tasks, isLoading, error } = useQuery({
    queryKey: ["tasks"],
    queryFn: fetchTasks,
  });

  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");

  const mutation = useMutation({
    mutationFn: createTask,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["tasks"] });
      setTitle("");
      setDescription("");
    },
  });

  return (
    <section className="card">
      <header className="card-header">
        <div>
          <p className="eyebrow">Dodzai</p>
          <h1>Task tracker</h1>
        </div>
        <span className="pill">API: {API_URL}</span>
      </header>
      <div className="grid">
        <div className="panel">
          <h2>Create a task</h2>
          <form
            className="stack"
            onSubmit={(event) => {
              event.preventDefault();
              mutation.mutate({ title, description });
            }}
          >
            <label className="field">
              <span>Title</span>
              <input
                value={title}
                onChange={(event) => setTitle(event.target.value)}
                placeholder="Write an actionable task"
                required
              />
            </label>
            <label className="field">
              <span>Description</span>
              <textarea
                value={description}
                onChange={(event) => setDescription(event.target.value)}
                placeholder="Optional context and notes"
                rows={4}
              />
            </label>
            <button type="submit" disabled={mutation.isPending}>
              {mutation.isPending ? "Saving..." : "Add task"}
            </button>
            {mutation.isError && <p className="error">{mutation.error.message}</p>}
          </form>
        </div>
        <div className="panel">
          <h2>Recent tasks</h2>
          {isLoading && <p>Loading tasks...</p>}
          {error && <p className="error">{error.message}</p>}
          <ul className="tasks">
            {tasks?.map((task) => (
              <li key={task.id} className="task">
                <div>
                  <p className="eyebrow">{new Date(task.created_at).toLocaleString()}</p>
                  <p className="task-title">{task.title}</p>
                  {task.description ? <p className="muted">{task.description}</p> : null}
                </div>
                <span className="pill">{task.status}</span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

export default function App() {
  return (
    <main className="shell">
      <TaskList />
    </main>
  );
}
