import * as React from "react";
import { cn } from "@/lib/utils";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  size?: "default" | "sm" | "lg";
  variant?: "default" | "outline" | "ghost";
}

export const Button = React.forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, size = "default", variant = "default", ...props }, ref) => {
    return (
      <button
        ref={ref}
        className={cn(
          "inline-flex items-center justify-center font-medium transition-all disabled:opacity-50 disabled:pointer-events-none active:scale-[0.98]",
          size === "sm" && "px-3 py-1.5 text-xs rounded-xl",
          size === "default" && "px-4 py-2 text-sm rounded-xl",
          size === "lg" && "px-6 py-3 text-base rounded-2xl",
          variant === "default" && "bg-[#3B82F6] hover:bg-[#2563EB] text-white shadow-sm",
          variant === "outline" && "border border-white/10 hover:bg-white/5 text-white",
          variant === "ghost" && "hover:bg-white/5 text-slate-300 hover:text-white",
          className
        )}
        {...props}
      />
    );
  }
);
Button.displayName = "Button";
