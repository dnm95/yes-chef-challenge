import { cookies } from "next/headers";
import Dashboard from "./components/dashboard";
import LoginForm from "./components/login";

export default async function Home() {
  // 1. Retrieve the session cookie server-side
  const cookieStore = await cookies();
  const isAuthenticated = cookieStore.has("is_authenticated");

  // 2. Conditional Rendering based on Auth State
  if (isAuthenticated) {
    return <Dashboard />;
  }

  return <LoginForm />
}
