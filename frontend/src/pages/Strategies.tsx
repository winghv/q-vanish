import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from 'react-query';
import { getStrategies, createStrategy, type Strategy } from '../services/api';

// Use the global showNotification function from App.tsx
declare global {
  interface Window {
    showNotification: (message: string, type?: 'success' | 'error' | 'info') => void;
  }
}

interface StrategyFormData {
  name: string;
  description: string;
  is_public: boolean;
}

const Strategies: React.FC = () => {
  const queryClient = useQueryClient();
  const [searchTerm, setSearchTerm] = useState('');
  const [isCreating, setIsCreating] = useState(false);
  const [formData, setFormData] = useState<StrategyFormData>({
    name: '',
    description: '',
    is_public: false
  });
  const [formErrors, setFormErrors] = useState<{name?: string}>({});

  // Fetch strategies
  const { data: strategies = [], isLoading, isError, error } = useQuery<Strategy[]>('strategies', getStrategies);

  // Filter strategies based on search term
  const filteredStrategies = strategies.filter(strategy =>
    strategy.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    (strategy.description && strategy.description.toLowerCase().includes(searchTerm.toLowerCase()))
  );

  // Create strategy mutation
  const createStrategyMutation = useMutation(createStrategy, {
    onSuccess: () => {
      queryClient.invalidateQueries('strategies');
      window.showNotification('策略创建成功', 'success');
      setIsCreating(false);
      setFormData({ name: '', description: '', is_public: false });
    },
    onError: (error: any) => {
      window.showNotification(error.response?.data?.detail || '创建策略失败', 'error');
    }
  });

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: value
    }));
    // Clear error when user starts typing
    if (formErrors[name as keyof typeof formErrors]) {
      setFormErrors(prev => ({
        ...prev,
        [name]: undefined
      }));
    }
  };

  const handleCheckboxChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: checked
    }));
  };

  const validateForm = () => {
    const errors: {name?: string} = {};
    if (!formData.name.trim()) {
      errors.name = '策略名称不能为空';
    }
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    
    try {
      await createStrategyMutation.mutateAsync(formData);
    } catch (error) {
      console.error('Error creating strategy:', error);
    }
  };

  const getStatusColor = (isPublic: boolean) => {
    return isPublic ? 'bg-blue-100 text-blue-800' : 'bg-gray-100 text-gray-800';
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('zh-CN', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  if (isLoading) {
    return (
      <div className="p-6">
        <div className="animate-pulse">
          <div className="h-8 bg-gray-200 rounded w-1/3 mb-4"></div>
          <div className="h-4 bg-gray-200 rounded w-1/2 mb-6"></div>
          <div className="space-y-3">
            {[...Array(5)].map((_, i) => (
              <div key={i} className="h-16 bg-gray-100 rounded"></div>
            ))}
          </div>
        </div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="p-6">
        <div className="bg-red-50 border-l-4 border-red-400 p-4 mb-6">
          <div className="flex">
            <div className="flex-shrink-0">
              <svg className="h-5 w-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clipRule="evenodd" />
              </svg>
            </div>
            <div className="ml-3">
              <p className="text-sm text-red-700">
                获取策略列表失败: {error instanceof Error ? error.message : '未知错误'}
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      <div className="mb-6 flex justify-between items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">策略管理</h1>
          <p className="mt-1 text-sm text-gray-500">查看和管理您的量化交易策略</p>
        </div>
        <button
          onClick={() => setIsCreating(true)}
          className="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          disabled={isCreating}
        >
          创建新策略
        </button>
      </div>

      <div className="mb-6">
        <div className="relative rounded-md shadow-sm">
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <svg className="h-5 w-5 text-gray-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor">
              <path fillRule="evenodd" d="M8 4a4 4 0 100 8 4 4 0 000-8zM2 8a6 6 0 1110.89 3.476l4.817 4.817a1 1 0 01-1.414 1.414l-4.816-4.816A6 6 0 012 8z" clipRule="evenodd" />
            </svg>
          </div>
          <input
            type="text"
            className="focus:ring-blue-500 focus:border-blue-500 block w-full pl-10 pr-12 sm:text-sm border-gray-300 rounded-md h-10"
            placeholder="搜索策略..."
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>
      </div>

      <div className="bg-white shadow overflow-hidden sm:rounded-md">
        <ul className="divide-y divide-gray-200">
          {filteredStrategies.length > 0 ? (
            filteredStrategies.map((strategy) => (
              <li key={strategy.id}>
                <div className="px-4 py-4 sm:px-6 hover:bg-gray-50">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center">
                      <p className="text-sm font-medium text-blue-600 truncate">
                        {strategy.name}
                      </p>
                      <span className={`ml-2 px-2 inline-flex text-xs leading-5 font-semibold rounded-full ${getStatusColor(strategy.is_public)}`}>
                        {strategy.is_public ? '公开' : '私有'}
                      </span>
                    </div>
                    <div className="text-sm text-gray-500">
                      {formatDate(strategy.created_at)}
                    </div>
                  </div>
                  <div className="mt-2">
                    <p className="text-sm text-gray-500">
                      {strategy.description || '暂无描述'}
                    </p>
                  </div>
                  <div className="mt-2 flex justify-end space-x-2">
                    <button className="text-sm text-blue-600 hover:text-blue-900">
                      编辑
                    </button>
                    <button className="text-sm text-red-600 hover:text-red-900">
                      删除
                    </button>
                  </div>
                </div>
              </li>
            ))
          ) : (
            <li className="px-4 py-6 text-center text-gray-500">
              {searchTerm ? '没有找到匹配的策略' : '暂无策略，点击上方按钮创建'}
            </li>
          )}
        </ul>
      </div>

      {/* Create Strategy Modal */}
      {isCreating && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white p-6 rounded-lg w-11/12 max-w-2xl">
            <h2 className="text-xl font-bold mb-4">创建新策略</h2>
            <form onSubmit={handleSubmit}>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="name">
                  策略名称 *
                </label>
                <input
                  className={`shadow appearance-none border ${formErrors.name ? 'border-red-500' : ''} rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline`}
                  id="name"
                  name="name"
                  type="text"
                  placeholder="输入策略名称"
                  value={formData.name}
                  onChange={handleInputChange}
                />
                {formErrors.name && (
                  <p className="text-red-500 text-xs italic mt-1">{formErrors.name}</p>
                )}
              </div>
              <div className="mb-4">
                <label className="block text-gray-700 text-sm font-bold mb-2" htmlFor="description">
                  策略描述
                </label>
                <textarea
                  className="shadow appearance-none border rounded w-full py-2 px-3 text-gray-700 leading-tight focus:outline-none focus:shadow-outline"
                  id="description"
                  name="description"
                  placeholder="输入策略描述"
                  rows={4}
                  value={formData.description}
                  onChange={handleInputChange}
                />
              </div>
              <div className="mb-4">
                <label className="flex items-center">
                  <input
                    type="checkbox"
                    name="is_public"
                    className="form-checkbox h-4 w-4 text-blue-600 transition duration-150 ease-in-out"
                    checked={formData.is_public}
                    onChange={handleCheckboxChange}
                  />
                  <span className="ml-2 text-sm text-gray-700">公开策略（其他用户可见）</span>
                </label>
              </div>
              <div className="flex items-center justify-end">
                <button
                  type="button"
                  onClick={() => {
                    setIsCreating(false);
                    setFormData({ name: '', description: '', is_public: false });
                    setFormErrors({});
                  }}
                  className="bg-gray-500 hover:bg-gray-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline mr-2"
                  disabled={createStrategyMutation.isLoading}
                >
                  取消
                </button>
                <button
                  type="submit"
                  className="bg-blue-500 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded focus:outline-none focus:shadow-outline"
                  disabled={createStrategyMutation.isLoading}
                >
                  {createStrategyMutation.isLoading ? '创建中...' : '创建策略'}
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
