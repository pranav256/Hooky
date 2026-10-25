import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: "default" | "sm" | "lg";
  variant?: "default" | "gold" | "outline" | "ghost";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size = "default", variant = "gold", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-all duration-150 disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]",
          size === "sm" && "px-3 py-1.5 text-xs rounded-xl",
          size === "default" && "px-4 py-2 text-sm rounded-xl",
          size === "lg" && "px-6 py-3 text-base rounded-2xl",
          variant === "gold" && "bg-gradient-to-r from-[#E5C07B] via-[#D4AF37] to-[#C99E2A] text-[#0A0D14] font-semibold hover:brightness-110 shadow-sm shadow-[#D4AF37]/20 border border-[#F3DFA2]/30",
          variant === "default" && "bg-[#1E2536] hover:bg-[#283248] text-white border border-white/10 shadow-sm",
          variant === "outline" && "border border-white/10 hover:bg-white/5 text-slate-200 hover:text-white",
          variant === "ghost" && "hover:bg-white/5 text-slate-400 hover:text-white",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
