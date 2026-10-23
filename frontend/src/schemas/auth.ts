import { z } from "zod";

export const passwordRule = z.string().min(10, "Use at least 10 characters.").regex(/[A-Za-z]/, "Include a letter.").regex(/\d/, "Include a number.");
export const loginSchema = z.object({ email: z.string().email("Enter a valid email."), password: z.string().min(1, "Enter your password.") });
export const registerSchema = z.object({ full_name: z.string().trim().min(1, "Enter your name.").max(120), email: z.string().email("Enter a valid email."), password: passwordRule });
export type LoginForm = z.infer<typeof loginSchema>;
export type RegisterForm = z.infer<typeof registerSchema>;
