import React, { useState, useEffect } from 'react';

interface Strategy {
  id: number;
  name: string;
  description: string;
  status: 'active' | 'inactive' | 'testing';
  performance: {
    return: number;
    sharpe: number;
    drawdown: number;
  };
  createdAt: string;
}

const mockStrategies: Strategy[] = [
  {
    id: 1,
    name: '均线突破策略',
    description: '基于50日均线和200日均线的金叉死叉策略',
    status: 'active',
    performance: {
      return: 12.5,
      sharpe: 1.2,
      drawdown: 8.3,
    },
    createdAt: '2023-05-15',
  },
  {
    id: 2,
    name: '动量反转策略',
    description: '基于RSI指标的超买超卖反转策略',
    status: 'testing',
    performance: {
      return: 8.3,
      sharpe: 0.9,
      drawdown: 12.1,
    },
    createdAt: '2023-06-21',
  },
  {
    id: 3,
    name: '波动率突破策略',
    description: '基于布林带的波动率突破策略',
    status: 'inactive',
    performance: {
      return: 15.7,
      sharpe: 1.5,
      drawdown: 10.2,
    },
    createdAt: '2023-04-10',
  },
];

const Strategies: React.FC = () => {
  const [strategies, setStrategies] = useState<Strategy[]>([]);
  const [isCreating, setIsCreating] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => {
    // 在实际应用中，这里应该是从API获取策略列表
    setStrategies(mockStrategies);
  }, []);

  const filteredStrategies = strategies.filter(strategy => 
    strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    strategy.description.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'active':
        return 'bg-green-100 text-green-800';
      case 'testing':
        return 'bg-yellow-100 text-yellow-800';
      case 'inactive':
        return 'bg-gray-100 text-gray-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  return (
    <div className="p-6">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold text-gray-800">策略管理</h1>
        <button
          onClick={() => setIsCreating(true)}
          className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700 transition"
        >
          创建新策略
        </button>
      </div>

      <div className="mb-6">
        <input
          type="text"
          placeholder="搜索策略..."
          className="w-full p-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />
      </div>

      <div className="bg-white rounded-lg shadow overflow-hidden">
        <table className="min-w-full divide-y divide-gray-200">
          <thead className="bg-gray-50">
            <tr>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                策略名称
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                描述
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                状态
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                表现
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                创建日期
              </th>
              <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                操作
              </th>
            </tr>
          </thead>
          <tbody className="bg-white divide-y divide-gray-200">
            {filteredStrategies.map((strategy) => (
              <tr key={strategy.id}>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm font-medium text-gray-900">{strategy.name}</div>
                </td>
                <td className="px-6 py-4">
                  <div className="text-sm text-gray-500">{strategy.description}</div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <span className={`px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(strategy.status)}`}>
                    {strategy.status === 'active' ? '运行中' : strategy.status === 'testing' ? '测试中' : '已停止'}
                  </span>
                </td>
                <td className="px-6 py-4 whitespace-nowrap">
                  <div className="text-sm text-gray-900">
                    <div>收益率: {strategy.performance.return}%</div>
                    <div>夏普比: {strategy.performance.sharpe}</div>
                    <div>最大回撤: {strategy.performance.drawdown}%</div>
                  </div>
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {strategy.createdAt}
                </td>
                <td className="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                  <button className="text-blue-600 hover:text-blue-900 mr-3">编辑</button>
                  <button className="text-red-600 hover:text-red-900">删除</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isCreating && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center">
          <div className="bg-white p-6 rounded-lg w-1/2">
            <h2 className="text-xl font-bold mb-4">创建新策略</h2>
            <form>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="name">
                  策略名称
                </label>
                <input
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="name"
                  type="text"
                  placeholder="输入策略名称"
                />
              </div>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="description">
                  策略描述
                </label>
                <textarea
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="description"
                  placeholder="输入策略描述"
                  rows={4}
                />
              </div>
              <div className="flex items-center justify-end">
                <button
                  className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline mr-2"
                  type="button"
                  onClick={() => setIsCreating(false)}
                >
                  取消
                </button>
                <button
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                  type="button"
                >
                  创建
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};

export default Strategies; 