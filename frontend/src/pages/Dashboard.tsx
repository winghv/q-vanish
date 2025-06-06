import { useState } from 'react';
import {
  LineChart,
  Line,
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';

// 模拟数据
const performanceData = [
  { date: '2023-01', value: 4000 },
  { date: '2023-02', value: 4200 },
  { date: '2023-03', value: 4100 },
  { date: '2023-04', value: 4400 },
  { date: '2023-05', value: 4600 },
  { date: '2023-06', value: 4800 },
  { date: '2023-07', value: 5000 },
  { date: '2023-08', value: 5200 },
  { date: '2023-09', value: 5400 },
];

const activeStrategies = [
  { id: 1, name: '双均线策略', profit: '+8.2%', trades: 32, status: 'running' },
  { id: 2, name: '趋势跟踪策略', profit: '+5.6%', trades: 18, status: 'running' },
  { id: 3, name: '波动率突破', profit: '-2.3%', trades: 24, status: 'paused' },
];

const recentTrades = [
  { id: 1, strategy: '双均线策略', symbol: 'AAPL', type: 'buy', price: '186.40', amount: '10', time: '2023-09-15 09:34' },
  { id: 2, strategy: '趋势跟踪策略', symbol: 'TSLA', type: 'sell', price: '264.79', amount: '5', time: '2023-09-14 15:21' },
  { id: 3, strategy: '波动率突破', symbol: 'NVDA', type: 'buy', price: '435.20', amount: '3', time: '2023-09-13 10:12' },
];

const notifications = [
  { id: 1, message: '双均线策略触发买入信号: AAPL', time: '10分钟前' },
  { id: 2, message: '趋势跟踪策略执行止损: TSLA', time: '2小时前' },
  { id: 3, message: '波动率突破策略回测完成', time: '昨天' },
];

const Dashboard: React.FC = () => {
  const [period, setPeriod] = useState<'1w'|'1m'|'3m'|'6m'|'1y'>('3m');

  return (
    <div className="space-y-6">
      {/* Page header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-semibold text-secondary-900">交易仪表盘</h1>
        <div className="flex gap-2">
          <button className="btn btn-primary">添加策略</button>
          <button className="btn btn-secondary">导出数据</button>
        </div>
      </div>

      {/* Portfolio Performance */}
      <div className="card">
        <div className="flex items-center justify-between mb-6">
          <h2 className="text-lg font-medium">组合表现</h2>
          <div className="flex space-x-2">
            {(['1w', '1m', '3m', '6m', '1y'] as const).map((p) => (
              <button
                key={p}
                onClick={() => setPeriod(p)}
                className={`px-3 py-1 text-sm rounded ${
                  period === p
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-secondary-600 hover:bg-secondary-100'
                }`}
              >
                {p}
              </button>
            ))}
          </div>
        </div>

        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart
              data={performanceData}
              margin={{ top: 10, right: 30, left: 0, bottom: 0 }}
            >
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis 
                dataKey="date" 
                tick={{ fontSize: 12 }} 
                tickFormatter={(value) => value.split('-')[1]}
              />
              <YAxis tick={{ fontSize: 12 }} />
              <Tooltip />
              <Area 
                type="monotone" 
                dataKey="value" 
                stroke="#6366f1" 
                fill="#e0e7ff" 
                fillOpacity={0.8}
              />
            </AreaChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        {/* Active Strategies */}
        <div className="card">
          <h2 className="mb-4 text-lg font-medium">活跃策略</h2>
          <div className="overflow-hidden">
            <table className="min-w-full">
              <thead>
                <tr className="border-b border-secondary-200">
                  <th className="py-3 text-left text-sm font-medium text-secondary-500">策略名称</th>
                  <th className="py-3 text-right text-sm font-medium text-secondary-500">收益</th>
                  <th className="py-3 text-right text-sm font-medium text-secondary-500">交易数</th>
                  <th className="py-3 text-right text-sm font-medium text-secondary-500">状态</th>
                </tr>
              </thead>
              <tbody>
                {activeStrategies.map((strategy) => (
                  <tr key={strategy.id} className="hover:bg-secondary-50">
                    <td className="py-4 text-sm font-medium text-secondary-900">{strategy.name}</td>
                    <td className={`py-4 text-right text-sm ${
                      strategy.profit.startsWith('+') ? 'text-green-600' : 'text-red-600'
                    }`}>
                      {strategy.profit}
                    </td>
                    <td className="py-4 text-right text-sm text-secondary-500">{strategy.trades}</td>
                    <td className="py-4 text-right">
                      <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                        strategy.status === 'running' 
                          ? 'bg-green-100 text-green-800'
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {strategy.status === 'running' ? '运行中' : '已暂停'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        {/* Recent Notifications */}
        <div className="card">
          <h2 className="mb-4 text-lg font-medium">最近通知</h2>
          <div className="space-y-4">
            {notifications.map((notification) => (
              <div key={notification.id} className="p-3 bg-secondary-50 rounded-lg">
                <div className="flex justify-between">
                  <p className="text-sm font-medium text-secondary-900">{notification.message}</p>
                  <span className="text-xs text-secondary-500">{notification.time}</span>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Recent Trades */}
      <div className="card">
        <h2 className="mb-4 text-lg font-medium">最近交易</h2>
        <div className="overflow-x-auto">
          <table className="min-w-full">
            <thead>
              <tr className="border-b border-secondary-200">
                <th className="py-3 text-left text-sm font-medium text-secondary-500">策略</th>
                <th className="py-3 text-left text-sm font-medium text-secondary-500">股票</th>
                <th className="py-3 text-left text-sm font-medium text-secondary-500">类型</th>
                <th className="py-3 text-right text-sm font-medium text-secondary-500">价格</th>
                <th className="py-3 text-right text-sm font-medium text-secondary-500">数量</th>
                <th className="py-3 text-right text-sm font-medium text-secondary-500">时间</th>
              </tr>
            </thead>
            <tbody>
              {recentTrades.map((trade) => (
                <tr key={trade.id} className="hover:bg-secondary-50">
                  <td className="py-4 text-sm text-secondary-900">{trade.strategy}</td>
                  <td className="py-4 text-sm font-medium text-secondary-900">{trade.symbol}</td>
                  <td className="py-4">
                    <span className={`inline-flex items-center px-2 py-1 text-xs font-medium rounded-full ${
                      trade.type === 'buy' 
                        ? 'bg-green-100 text-green-800'
                        : 'bg-red-100 text-red-800'
                    }`}>
                      {trade.type === 'buy' ? '买入' : '卖出'}
                    </span>
                  </td>
                  <td className="py-4 text-right text-sm text-secondary-900">${trade.price}</td>
                  <td className="py-4 text-right text-sm text-secondary-900">{trade.amount}</td>
                  <td className="py-4 text-right text-sm text-secondary-500">{trade.time}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};

export default Dashboard; 