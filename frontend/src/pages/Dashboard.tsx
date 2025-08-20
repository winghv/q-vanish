import { useState, useEffect } from 'react';
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
import {
  getDashboardPerformance,
  getActiveStrategies,
  getRecentTrades,
  getNotifications
} from '../services/api';

const Dashboard: React.FC = () => {
  const [period, setPeriod] = useState<'1w'|'1m'|'3m'|'6m'|'1y'>('3m');
  const [performanceData, setPerformanceData] = useState<{date: string, value: number}[]>([]);
  const [activeStrategies, setActiveStrategies] = useState<any[]>([]);
  const [recentTrades, setRecentTrades] = useState<any[]>([]);
  const [notifications, setNotifications] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [perf, strategies, trades, notifs] = await Promise.all([
          getDashboardPerformance(),
          getActiveStrategies(),
          getRecentTrades(),
          getNotifications()
        ]);
        setPerformanceData(perf);
        setActiveStrategies(strategies);
        setRecentTrades(trades);
        setNotifications(notifs);
      } catch (err) {
        window.showNotification?.('获取仪表盘数据失败', 'error');
      }
      setIsLoading(false);
    };
    fetchData();
  }, []);

  if (isLoading) {
    return <div className="p-6 text-gray-400">加载中...</div>;
  }

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
                      String(strategy.profit).startsWith('+') ? 'text-green-600' : 'text-red-600'
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