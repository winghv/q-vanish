import React, { useState } from 'react';

const Backtest: React.FC = () => {
  const [formData, setFormData] = useState({
    strategy: '',
    startDate: '',
    endDate: '',
    initialCapital: 10000,
    symbol: '',
  });
  
  const [isLoading, setIsLoading] = useState(false);
  const [results, setResults] = useState<any>(null);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setIsLoading(true);
    
    // 模拟API调用
    setTimeout(() => {
      setResults({
        totalReturn: 15.7,
        annualReturn: 8.2,
        sharpeRatio: 1.3,
        maxDrawdown: -12.5,
        winRate: 0.62,
        trades: 124,
        equity: [
          { date: '2023-01-01', value: 10000 },
          { date: '2023-02-01', value: 10200 },
          { date: '2023-03-01', value: 10500 },
          { date: '2023-04-01', value: 10300 },
          { date: '2023-05-01', value: 10800 },
          { date: '2023-06-01', value: 11200 },
        ]
      });
      setIsLoading(false);
    }, 1500);
  };

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">策略回测</h1>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="md:col-span-1">
          <div className="bg-white rounded-lg shadow p-6">
            <h2 className="text-lg font-semibold mb-4">回测参数</h2>
            
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  选择策略
                </label>
                <select
                  name="strategy"
                  value={formData.strategy}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded"
                  required
                >
                  <option value="">选择策略</option>
                  <option value="ma_crossover">均线交叉策略</option>
                  <option value="rsi_reversal">RSI反转策略</option>
                  <option value="bollinger_breakout">布林带突破策略</option>
                </select>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  股票/加密货币代码
                </label>
                <input
                  type="text"
                  name="symbol"
                  placeholder="例如: AAPL, BTC-USD"
                  value={formData.symbol}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded"
                  required
                />
              </div>
              
              <div className="grid grid-cols-2 gap-4 mb-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    开始日期
                  </label>
                  <input
                    type="date"
                    name="startDate"
                    value={formData.startDate}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded"
                    required
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-1">
                    结束日期
                  </label>
                  <input
                    type="date"
                    name="endDate"
                    value={formData.endDate}
                    onChange={handleChange}
                    className="w-full p-2 border border-gray-300 rounded"
                    required
                  />
                </div>
              </div>
              
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  初始资金
                </label>
                <input
                  type="number"
                  name="initialCapital"
                  value={formData.initialCapital}
                  onChange={handleChange}
                  className="w-full p-2 border border-gray-300 rounded"
                  min="1000"
                  required
                />
              </div>
              
              <button
                type="submit"
                className="w-full bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition"
                disabled={isLoading}
              >
                {isLoading ? '回测中...' : '开始回测'}
              </button>
            </form>
          </div>
        </div>
        
        <div className="md:col-span-2">
          {isLoading ? (
            <div className="flex justify-center items-center h-64 bg-white rounded-lg shadow">
              <p className="text-lg text-gray-600">正在进行回测分析...</p>
            </div>
          ) : results ? (
            <div className="bg-white rounded-lg shadow p-6">
              <h2 className="text-lg font-semibold mb-4">回测结果</h2>
              
              <div className="grid grid-cols-2 md:grid-cols-3 gap-4 mb-6">
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">总收益</p>
                  <p className="text-xl font-bold text-green-600">+{results.totalReturn}%</p>
                </div>
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">年化收益</p>
                  <p className="text-xl font-bold text-green-600">+{results.annualReturn}%</p>
                </div>
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">夏普比率</p>
                  <p className="text-xl font-bold">{results.sharpeRatio}</p>
                </div>
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">最大回撤</p>
                  <p className="text-xl font-bold text-red-600">{results.maxDrawdown}%</p>
                </div>
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">胜率</p>
                  <p className="text-xl font-bold">{Math.round(results.winRate * 100)}%</p>
                </div>
                <div className="bg-gray-50 p-4 rounded">
                  <p className="text-sm text-gray-500">交易次数</p>
                  <p className="text-xl font-bold">{results.trades}</p>
                </div>
              </div>
              
              <div>
                <h3 className="text-md font-semibold mb-2">权益曲线</h3>
                <div className="h-64 bg-gray-50 rounded flex items-center justify-center">
                  <p className="text-gray-500">这里将显示权益曲线图表</p>
                </div>
              </div>
            </div>
          ) : (
            <div className="flex justify-center items-center h-64 bg-white rounded-lg shadow">
              <p className="text-gray-500">请设置回测参数并开始回测</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Backtest; 