"use client";

import { memo } from "react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";

const MarkdownTextImpl = () => {
  return (
    <MarkdownTextPrimitive
      className="aui-md prose prose-sm dark:prose-invert max-w-none"
    />
  );
};

export const MarkdownText = memo(MarkdownTextImpl);
