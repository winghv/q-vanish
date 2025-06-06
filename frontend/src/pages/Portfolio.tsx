import React, { useState } from 'react';

interface Asset {
  symbol: string;
  name: string;
  shares: number;
  price: number;
  value: number;
  allocation: number;
  dayChange: number;
  totalReturn: number;
}

interface Performance {
  balance: number;
  dayChange: number;
  weekChange: number;
  monthChange: number;
  yearChange: number;
  totalReturn: number;
  history: { date: string; value: number }[];
}

const mockAssets: Asset[] = [
  {
    symbol: 'AAPL',
    name: 'Apple Inc.',
    shares: 10,
    price: 165.30,
    value: 1653.00,
    allocation: 35.2,
    dayChange: 1.5,
    totalReturn: 10.02,
  },
  {
    symbol: 'MSFT',
    name: 'Microsoft Corporation',
    shares: 5,
    price: 275.20,
    value: 1376.00,
    allocation: 29.3,
    dayChange: -0.8,
    totalReturn: -1.89,
  },
  {
    symbol: 'TSLA',
    name: 'Tesla, Inc.',
    shares: 3,
    price: 244.30,
    value: 732.90,
    allocation: 15.6,
    dayChange: 2.3,
    totalReturn: 15.92,
  },
  {
    symbol: 'AMZN',
    name: 'Amazon.com, Inc.',
    shares: 2,
    price: 113.50,
    value: 227.00,
    allocation: 4.8,
    dayChange: 0.5,
    totalReturn: 5.35,
  },
  {
    symbol: 'NVDA',
    name: 'NVIDIA Corporation',
    shares: 2,
    price: 370.80,
    value: 741.60,
    allocation: 15.8,
    dayChange: 3.2,
    totalReturn: 22.75,
  },
];

const mockPerformance: Performance = {
  balance: 4730.50,
  dayChange: 1.2,
  weekChange: 2.5,
  monthChange: -1.8,
  yearChange: 8.4,
  totalReturn: 12.3,
  history: [
    { date: '2023-01-01', value: 4000 },
    { date: '2023-02-01', value: 4120 },
    { date: '2023-03-01', value: 4350 },
    { date: '2023-04-01', value: 4280 },
    { date: '2023-05-01', value: 4520 },
    { date: '2023-06-01', value: 4730.50 },
  ]
};

const Portfolio: React.FC = () => {
  const [assets] = useState<Asset[]>(mockAssets);
  const [performance] = useState<Performance>(mockPerformance);
  const [activeTab, setActiveTab] = useState<'assets' | 'performance'>('assets');

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">投资组合</h1>
      
      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">总资产</h2>
          <div className="text-2xl font-bold">${performance.balance.toFixed(2)}</div>
          <div className={`mt-2 text-sm ${performance.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {performance.dayChange >= 0 ? '↑' : '↓'} {Math.abs(performance.dayChange)}% 今日
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">总收益</h2>
          <div className="text-2xl font-bold">${(performance.balance * performance.totalReturn / 100).toFixed(2)}</div>
          <div className={`mt-2 text-sm ${performance.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}`}>
            {performance.totalReturn >= 0 ? '+' : ''}{performance.totalReturn}%
          </div>
        </div>
        
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">收益率</h2>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <div className="text-xs text-gray-500">日</div>
              <div className={`text-sm font-medium ${performance.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {performance.dayChange >= 0 ? '+' : ''}{performance.dayChange}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">周</div>
              <div className={`text-sm font-medium ${performance.weekChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {performance.weekChange >= 0 ? '+' : ''}{performance.weekChange}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">月</div>
              <div className={`text-sm font-medium ${performance.monthChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {performance.monthChange >= 0 ? '+' : ''}{performance.monthChange}%
              </div>
            </div>
            <div>
              <div className="text-xs text-gray-500">年</div>
              <div className={`text-sm font-medium ${performance.yearChange >= 0 ? 'text-green-600' : 'text-red-600'}`}>
                {performance.yearChange >= 0 ? '+' : ''}{performance.yearChange}%
              </div>
            </div>
          </div>
        </div>
      </div>
      
      {/* 图表和资产列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="border-b">
          <div className="flex">
            <button
              className={`py-4 px-6 ${activeTab === 'assets' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-gray-500'}`}
              onClick={() => setActiveTab('assets')}
            >
              资产配置
            </button>
            <button
              className={`py-4 px-6 ${activeTab === 'performance' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-gray-500'}`}
              onClick={() => setActiveTab('performance')}
            >
              收益表现
            </button>
          </div>
        </div>
        
        <div className="p-6">
          {activeTab === 'assets' ? (
            <div>
              <div className="h-64 bg-gray-50 rounded mb-6 flex items-center justify-center">
                <p className="text-gray-500">这里将显示资产配置饼图</p>
              </div>
              
              <table className="min-w-full divide-y divide-gray-200">
                <thead className="bg-gray-50">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">资产</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">数量</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">价格</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">市值</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">配置比例</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">日涨跌</th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">总收益</th>
                  </tr>
                </thead>
                <tbody className="bg-white divide-y divide-gray-200">
                  {assets.map((asset) => (
                    <tr key={asset.symbol}>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <div className="flex items-center">
                          <div className="ml-4">
                            <div className="text-sm font-medium text-gray-900">{asset.symbol}</div>
                            <div className="text-sm text-gray-500">{asset.name}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">{asset.shares}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${asset.price.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">${asset.value.toFixed(2)}</td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                        <div className="w-full bg-gray-200 rounded-full h-2.5">
                          <div 
                            className="bg-blue-600 h-2.5 rounded-full" 
                            style={{ width: `${asset.allocation}%` }}
                          ></div>
                        </div>
                        <span className="text-xs">{asset.allocation.toFixed(1)}%</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={asset.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {asset.dayChange >= 0 ? '+' : ''}{asset.dayChange}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={asset.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {asset.totalReturn >= 0 ? '+' : ''}{asset.totalReturn}%
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <div>
              <div className="h-64 bg-gray-50 rounded mb-6 flex items-center justify-center">
                <p className="text-gray-500">这里将显示收益曲线图</p>
              </div>
              
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="bg-gray-50 rounded p-4">
                  <h3 className="text-lg font-medium mb-4">收益统计</h3>
                  <div className="space-y-3">
                    <div className="flex justify-between">
                      <span className="text-gray-600">日涨跌幅</span>
                      <span className={performance.dayChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {performance.dayChange >= 0 ? '+' : ''}{performance.dayChange}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">周涨跌幅</span>
                      <span className={performance.weekChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {performance.weekChange >= 0 ? '+' : ''}{performance.weekChange}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">月涨跌幅</span>
                      <span className={performance.monthChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {performance.monthChange >= 0 ? '+' : ''}{performance.monthChange}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">年涨跌幅</span>
                      <span className={performance.yearChange >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {performance.yearChange >= 0 ? '+' : ''}{performance.yearChange}%
                      </span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">总收益率</span>
                      <span className={performance.totalReturn >= 0 ? 'text-green-600' : 'text-red-600'}>
                        {performance.totalReturn >= 0 ? '+' : ''}{performance.totalReturn}%
                      </span>
                    </div>
                  </div>
                </div>
                
                <div className="bg-gray-50 rounded p-4">
                  <h3 className="text-lg font-medium mb-4">历史净值</h3>
                  <div className="space-y-2">
                    {performance.history.map((entry, index) => (
                      <div key={index} className="flex justify-between">
                        <span className="text-gray-600">{entry.date}</span>
                        <span className="font-medium">${entry.value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
      
      {/* 操作按钮 */}
      <div className="flex justify-end">
        <button className="bg-blue-600 text-white py-2 px-4 rounded hover:bg-blue-700 transition mr-2">
          调整配置
        </button>
        <button className="bg-gray-600 text-white py-2 px-4 rounded hover:bg-gray-700 transition">
          导出报告
        </button>
      </div>
    </div>
  );
};

export default Portfolio; 