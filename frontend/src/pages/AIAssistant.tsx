import { useState, useRef, useEffect } from 'react';
import { SparklesIcon, PaperAirplaneIcon, ArrowPathIcon } from '@heroicons/react/24/outline';

interface Message {
  id: string;
  content: string;
  role: 'user' | 'assistant';
  timestamp: Date;
}

const AIAssistant: React.FC = () => {
  const [messages, setMessages] = useState<Message[]>([
    {
      id: '1',
      content: '你好！我是Q-Vanish的AI助手，我可以帮你分析市场、提供交易建议、优化你的策略，或者回答任何量化交易相关问题。',
      role: 'assistant',
      timestamp: new Date(),
    }
  ]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 滚动到最新消息
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const handleSendMessage = () => {
    if (!input.trim()) return;

    // 添加用户消息
    const userMessage: Message = {
      id: Date.now().toString(),
      content: input,
      role: 'user',
      timestamp: new Date(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput('');
    setIsLoading(true);

    // 模拟AI响应
    setTimeout(() => {
      const aiResponses = [
        "根据当前市场分析，科技板块有望走强，可以考虑增加对AAPL、MSFT等头部科技公司的布局。",
        "我分析了你的双均线策略，建议将快线周期从5天调整到8天，这可能会减少虚假信号并提高胜率。",
        "最近市场波动性较大，建议在策略中添加止损机制，可以考虑使用10%的移动止损来保护你的利润。",
        "基于最新的经济数据，建议减少对周期性行业的敞口，增加防御性板块的配置比例。",
        "你的策略回测结果显示，在熊市环境中表现不佳，可以考虑添加市场趋势过滤器来避免逆势交易。"
      ];
      
      const aiMessage: Message = {
        id: Date.now().toString(),
        content: aiResponses[Math.floor(Math.random() * aiResponses.length)],
        role: 'assistant',
        timestamp: new Date(),
      };
      
      setMessages((prev) => [...prev, aiMessage]);
      setIsLoading(false);
    }, 1000);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSendMessage();
    }
  };

  // 示例提示问题
  const suggestionPrompts = [
    "分析最近市场趋势",
    "优化我的双均线策略",
    "如何设置有效的止损位置",
    "量化交易的风险管理建议",
    "智能选择交易标的"
  ];

  return (
    <div className="flex flex-col h-[calc(100vh-130px)]">
      <h1 className="mb-4 text-2xl font-semibold text-secondary-900">AI交易助手</h1>

      {/* 消息对话框 */}
      <div className="flex-1 overflow-y-auto bg-white rounded-lg shadow mb-4">
        <div className="p-4 space-y-4">
          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === 'assistant' ? 'justify-start' : 'justify-end'}`}
            >
              <div
                className={`max-w-[80%] rounded-lg px-4 py-2 ${
                  message.role === 'assistant'
                    ? 'bg-primary-100 text-secondary-900'
                    : 'bg-secondary-200 text-secondary-900'
                }`}
              >
                <p className="text-sm">{message.content}</p>
                <p className="mt-1 text-xs text-secondary-500">
                  {message.timestamp.toLocaleTimeString()}
                </p>
              </div>
            </div>
          ))}
          {isLoading && (
            <div className="flex justify-start">
              <div className="max-w-[80%] rounded-lg px-4 py-2 bg-primary-100">
                <div className="flex items-center space-x-2">
                  <ArrowPathIcon className="w-5 h-5 text-primary-600 animate-spin" />
                  <span className="text-sm text-secondary-500">AI思考中...</span>
                </div>
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* 问题建议 */}
      <div className="mb-4 flex flex-wrap gap-2">
        {suggestionPrompts.map((prompt, index) => (
          <button
            key={index}
            onClick={() => setInput(prompt)}
            className="bg-secondary-100 hover:bg-secondary-200 text-secondary-700 text-sm py-1 px-3 rounded-full"
          >
            {prompt}
          </button>
        ))}
      </div>

      {/* 输入框 */}
      <div className="relative">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          className="w-full py-3 pl-4 pr-12 border border-secondary-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:border-primary-500 resize-none"
          placeholder="输入你的问题或交易想法..."
          rows={2}
          disabled={isLoading}
        />
        <button
          onClick={handleSendMessage}
          disabled={!input.trim() || isLoading}
          className="absolute right-2 bottom-2 p-2 rounded-full bg-primary-600 text-white disabled:bg-primary-400 disabled:cursor-not-allowed"
        >
          <PaperAirplaneIcon className="w-5 h-5" />
        </button>
      </div>
    </div>
  );
};

export default AIAssistant; 