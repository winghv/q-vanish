import React, { useState, useEffect } from 'react';
import { getAssets, getPerformance, Asset, Performance } from '../services/api';

const Portfolio: React.FC = () => {
  const [assets, setAssets] = useState<Asset[]>([]);
  const [performance, setPerformance] = useState<Performance | null>(null);
  const [activeTab, setActiveTab] = useState<'assets' | 'performance'>('assets');
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      setIsLoading(true);
      try {
        const [assetsRes, perfRes] = await Promise.all([
          getAssets(),
          getPerformance()
        ]);
        setAssets(assetsRes);
        setPerformance(perfRes);
      } catch (err) {
        window.showNotification?.('获取资产数据失败', 'error');
      }
      setIsLoading(false);
    };
    fetchData();
  }, []);

  if (isLoading || !performance) {
    return <div className="p-6 text-gray-400">加载中...</div>;
  }

  return (
    <div className="p-6">
      <h1 className="text-2xl font-bold text-gray-800 mb-6">投资组合</h1>
      {/* 概览卡片 */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">总资产</h2>
          <div className="text-2xl font-bold">${performance.balance.toFixed(2)}</div>
          <div className={`mt-2 text-sm ${performance.day_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.day_change >= 0 ? '↑' : '↓'} {Math.abs(performance.day_change)}% 今日</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">总收益</h2>
          <div className="text-2xl font-bold">${(performance.balance * performance.total_return / 100).toFixed(2)}</div>
          <div className={`mt-2 text-sm ${performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.total_return >= 0 ? '+' : ''}{performance.total_return}%</div>
        </div>
        <div className="bg-white rounded-lg shadow p-6">
          <h2 className="text-sm text-gray-500 mb-1">收益率</h2>
          <div className="grid grid-cols-2 gap-2 mt-2">
            <div>
              <div className="text-xs text-gray-500">日</div>
              <div className={`text-sm font-medium ${performance.day_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.day_change >= 0 ? '+' : ''}{performance.day_change}%</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">周</div>
              <div className={`text-sm font-medium ${performance.week_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.week_change >= 0 ? '+' : ''}{performance.week_change}%</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">月</div>
              <div className={`text-sm font-medium ${performance.month_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.month_change >= 0 ? '+' : ''}{performance.month_change}%</div>
            </div>
            <div>
              <div className="text-xs text-gray-500">年</div>
              <div className={`text-sm font-medium ${performance.year_change >= 0 ? 'text-green-600' : 'text-red-600'}`}>{performance.year_change >= 0 ? '+' : ''}{performance.year_change}%</div>
            </div>
          </div>
        </div>
      </div>
      {/* 图表和资产列表 */}
      <div className="bg-white rounded-lg shadow overflow-hidden mb-6">
        <div className="border-b">
          <div className="flex">
            <button className={`py-4 px-6 ${activeTab === 'assets' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-gray-500'}`} onClick={() => setActiveTab('assets')}>资产配置</button>
            <button className={`py-4 px-6 ${activeTab === 'performance' ? 'border-b-2 border-blue-600 text-blue-600 font-medium' : 'text-gray-500'}`} onClick={() => setActiveTab('performance')}>收益表现</button>
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
                          <div className="bg-blue-600 h-2.5 rounded-full" style={{ width: `${asset.allocation}%` }}></div>
                        </div>
                        <span className="text-xs">{asset.allocation.toFixed(1)}%</span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={asset.day_change >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {asset.day_change >= 0 ? '+' : ''}{asset.day_change}%
                        </span>
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-sm">
                        <span className={asset.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>
                          {asset.total_return >= 0 ? '+' : ''}{asset.total_return}%
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
                      <span className={performance.day_change >= 0 ? 'text-green-600' : 'text-red-600'}>{performance.day_change >= 0 ? '+' : ''}{performance.day_change}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">周涨跌幅</span>
                      <span className={performance.week_change >= 0 ? 'text-green-600' : 'text-red-600'}>{performance.week_change >= 0 ? '+' : ''}{performance.week_change}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">月涨跌幅</span>
                      <span className={performance.month_change >= 0 ? 'text-green-600' : 'text-red-600'}>{performance.month_change >= 0 ? '+' : ''}{performance.month_change}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">年涨跌幅</span>
                      <span className={performance.year_change >= 0 ? 'text-green-600' : 'text-red-600'}>{performance.year_change >= 0 ? '+' : ''}{performance.year_change}%</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-600">总收益率</span>
                      <span className={performance.total_return >= 0 ? 'text-green-600' : 'text-red-600'}>{performance.total_return >= 0 ? '+' : ''}{performance.total_return}%</span>
                    </div>
                  </div>
                </div>
                <div className="bg-gray-50 rounded p-4">
                  <h3 className="text-lg font-medium mb-4">历史净值</h3>
                  <div className="space-y-2">
                    {performance.history.map((item) => (
                      <div key={item.date} className="flex justify-between text-sm">
                        <span className="text-gray-500">{item.date}</span>
                        <span className="text-gray-900">${item.value.toFixed(2)}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Portfolio; 