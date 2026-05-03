"use client";

import {
  ComposerPrimitive,
  MessagePrimitive,
  ThreadPrimitive,
  SuggestionPrimitive,
  AuiIf,
} from "@assistant-ui/react";
import { SendHorizontalIcon, LoaderIcon } from "lucide-react";
import { type FC } from "react";
import { MarkdownText } from "./markdown-text";

export const Thread: FC = () => {
  return (
    <ThreadPrimitive.Root className="flex h-full flex-col bg-background">
      <ThreadPrimitive.Viewport className="flex flex-1 flex-col items-center overflow-y-auto scroll-smooth px-4 pt-8">
        <ThreadPrimitive.Empty>
          <div className="flex flex-col items-center gap-4 pt-20 animate-fade-in">
            <span className="text-4xl font-bold tracking-widest">ALO</span>
            <p className="text-muted-foreground text-center max-w-md">
              Ask me about ALO Yoga products, policies, shipping, returns,
              loyalty program, or customer orders.
            </p>
          </div>
        </ThreadPrimitive.Empty>

        <ThreadPrimitive.Messages
          components={{
            UserMessage,
            AssistantMessage,
          }}
        />

        {/* Typing indicator shown while the assistant is generating */}
        <AuiIf condition={(s) => s.thread.isRunning}>
          <div className="flex w-full max-w-2xl gap-3 mb-6 animate-fade-in">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-bold">
              ALO
            </div>
            <div className="flex items-center gap-2 pt-1 text-muted-foreground">
              <div className="typing-dots flex gap-1">
                <span className="typing-dot" />
                <span className="typing-dot" />
                <span className="typing-dot" />
              </div>
            </div>
          </div>
        </AuiIf>

        {/* Spacer pushes footer to bottom when few messages */}
        <div className="min-h-8 flex-grow" />

        {/* Footer: opaque background with gradient fade at top */}
        <ThreadPrimitive.ViewportFooter className="sticky bottom-0 z-10 mt-3 flex w-full max-w-2xl flex-col items-center justify-end pb-4">
          {/* Gradient fade overlay — messages disappear behind this */}
          <div className="pointer-events-none absolute inset-x-0 -top-12 h-12 bg-gradient-to-t from-background to-transparent" />
          {/* Solid opaque background for the composer area */}
          <div className="absolute inset-x-0 top-0 bottom-0 bg-background" />

          {/* Content sits above the opaque background */}
          <div className="relative z-10 w-full">
            <ThreadPrimitive.ScrollToBottom className="absolute -top-10 left-1/2 -translate-x-1/2 rounded-full border bg-background px-3 py-1.5 text-sm shadow-md transition-opacity hover:bg-muted" />
            <ThreadPrimitive.Suggestions>
              {() => <Suggestion />}
            </ThreadPrimitive.Suggestions>
            <Composer />
          </div>
        </ThreadPrimitive.ViewportFooter>
      </ThreadPrimitive.Viewport>
    </ThreadPrimitive.Root>
  );
};

const Suggestion: FC = () => {
  return (
    <SuggestionPrimitive.Trigger send asChild>
      <button className="mb-2 mr-2 inline-flex rounded-full border px-4 py-2 text-sm hover:bg-muted transition-colors animate-fade-in">
        <SuggestionPrimitive.Title />
      </button>
    </SuggestionPrimitive.Trigger>
  );
};

const Composer: FC = () => {
  return (
    <ComposerPrimitive.Root className="relative flex w-full items-end rounded-lg border bg-background shadow-sm transition-shadow focus-within:shadow-md">
      <ComposerPrimitive.Input
        autoFocus
        placeholder="Ask about ALO Yoga products, policies, or orders..."
        rows={1}
        className="placeholder:text-muted-foreground max-h-40 flex-1 resize-none border-none bg-transparent p-4 text-sm outline-none"
      />
      <ComposerPrimitive.Send className="m-2 flex h-8 w-8 items-center justify-center rounded-md bg-foreground text-background transition-opacity disabled:opacity-10">
        <SendHorizontalIcon className="size-4" />
      </ComposerPrimitive.Send>
    </ComposerPrimitive.Root>
  );
};

const UserMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="relative mb-6 flex w-full max-w-2xl flex-col items-end gap-2 animate-message-in">
      <div className="relative max-w-xl break-words rounded-3xl bg-muted px-5 py-2.5">
        <MessagePrimitive.Content />
      </div>
    </MessagePrimitive.Root>
  );
};

const AssistantMessage: FC = () => {
  return (
    <MessagePrimitive.Root className="relative mb-6 flex w-full max-w-2xl gap-3 animate-message-in">
      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full border bg-background text-xs font-bold">
        ALO
      </div>
      <div className="flex-1 pt-1">
        <MessagePrimitive.Parts
          components={{
            Text: MarkdownText,
          }}
        />
      </div>
    </MessagePrimitive.Root>
  );
};
