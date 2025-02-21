"use client";

import SearchResults from "@/components/SearchResults";
import { Button } from "@heroui/button";
import { Input, Textarea } from "@heroui/input";
import { ScrollShadow } from "@heroui/scroll-shadow";
import { Switch } from "@heroui/switch";
import { useState, useEffect, useRef } from "react";

export default function Chat() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [ws, setWs] = useState(null);
  const [chainMessages, setChainMessages] = useState({});
  const [searchEnabled, setSearchEnabled] = useState(false);
  const chatEndRef = useRef(null);

  useEffect(() => {
    const websocket = new WebSocket("ws://localhost:8000/chat");
    websocket.onopen = () => console.log("Connected to WebSocket");
    websocket.onmessage = (event) => {
      const data = JSON.parse(event.data);
      setMessages((prev) => {
        if (data?.chain_of_thought) {
          // Keep all user messages and only remove system messages where chain_of_thought is false
          return [
            ...prev?.filter(
              (msg) => msg?.chain_of_thought || msg?.user === "You"
            ),
            data,
          ];
        } else {
          // If the last message was also false and not from the user, override it
          if (
            prev?.length > 0 &&
            !prev[prev.length - 1]?.chain_of_thought &&
            prev[prev.length - 1]?.user !== "You"
          ) {
            return [...prev?.slice(0, -1), data];
          }
          return [...prev, data];
        }
      });
    };
    websocket.onclose = () => console.log("WebSocket disconnected");
    setWs(websocket);
    return () => websocket.close();
  }, []);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const formatMessage = (text) => {
    return text.split("\n").map((line, i) => (
      <span key={i}>
        {line
          .split(/(\*\*.*?\*\*)/)
          .map((chunk, j) =>
            chunk.startsWith("**") && chunk.endsWith("**") ? (
              <strong key={j}>{chunk.slice(2, -2)}</strong>
            ) : (
              chunk
            )
          )}
        <br />
      </span>
    ));
  };

  const sendMessage = () => {
    if (ws && input.trim()) {
      const messageData = {
        id: Date.now(),
        user_id: "user123",
        session_id: "session123",
        user_message: input,
        search: searchEnabled,
      };
      ws.send(JSON.stringify(messageData));
      setMessages((prev) => [...prev, { ...messageData, user: "You" }]);
      setInput("");
      setLoading(true);
    }
  };
  console.log(input);

  return (
    <div className="flex flex-col w-full  max-w-4xl mx-auto p-4  ">
      <ScrollShadow className="w-full overflow-x-hidden pb-[100px] h-[70vh] overflow-y-auto">
        {messages.map((msg, index) => (
          <div
            key={index}
            className={`mb-4 flex flex-col ${
              msg.user === "You" ? "items-end" : "items-start"
            }`}
          >
            {!msg?.chain_of_thought && msg.user !== "You" && (
              <div className="flex items-center gap-2 p-2  rounded-md mb-1">
                <div className="w-4 h-4 border-2 border-gray-500 border-t-transparent rounded-full animate-spin"></div>

                <p className="text-sm text-gray-500">
                  {msg?.chain_of_thought_message}
                </p>
              </div>
            )}
            {msg?.search_results && (
              <SearchResults results={msg?.search_results} />
            )}
            <p
              className={`p-2 rounded-lg text-sm max-w-[500px]  break-words whitespace-pre-line  ${
                msg.user === "You"
                  ? "bg-[#F3F3F3] text-gray-900 dark:text-gray-100 dark:bg-gray-800"
                  : "text-gray-900 dark:bg-gray-700 dark:text-gray-100"
              }`}
            >
              {formatMessage(msg.user_message || msg.message)}
            </p>
          </div>
        ))}
        <div ref={chatEndRef}></div>
      </ScrollShadow>

      <div className="flex bg-gray-900 gap-2 mt-2 relative">
        {/* <Input
          type="text"
          
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
        /> */}
        <Textarea
          //  radius="none"
          id="txt-round"
          className="absolute  w-full bottom-[2.9rem] pb-0  rounded-t-xl "
          minRows={1}
          maxRows={4}
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Type a message..."
        />
        <div className="flex bg-[#f4f4f5] p-2 dark:bg-[#27272a] rounded-b-xl items-center justify-between w-full  absolute bottom-0 ">
          <Switch
            isSelected={searchEnabled}
            onValueChange={setSearchEnabled}
            aria-label="Search"
          >
            Search
          </Switch>
          <Button
            onPress={sendMessage}
            className="p-2 bg-blue-500 text-white rounded-lg"
          >
            Send
          </Button>
        </div>
      </div>
    </div>
  );
}
