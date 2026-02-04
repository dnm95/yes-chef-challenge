"use server";

import { cookies } from "next/headers";

export async function loginAction(formData: FormData) {
  const password = formData.get("password");

  const cookiesStore = await cookies();
  
  // Verify against environment variable
  if (password === process.env.ACCESS_PASSWORD) {
    // Set secure httpOnly cookie
    cookiesStore.set("is_authenticated", "true", {
      httpOnly: true, // Not accessible via client-side JS
      secure: process.env.NODE_ENV === "production",
      maxAge: 60 * 60 * 24 * 7, // 1 week session
      path: "/",
    });
    return { success: true };
  } else {
    return { success: false, message: "Incorrect password. Please try again." };
  }
}
