import { Link } from 'react-router-dom';

const NotFound = () => {
  return (
    <div className="flex flex-col items-center justify-center h-[70vh] text-center px-4">
      <h1 className="text-6xl font-bold text-primary-600">404</h1>
      <h2 className="mt-4 text-3xl font-semibold text-secondary-900">页面未找到</h2>
      <p className="mt-2 text-lg text-secondary-600">
        很抱歉，您请求的页面不存在或已被移除。
      </p>
      <Link
        to="/dashboard"
        className="mt-8 btn btn-primary"
      >
        返回仪表盘
      </Link>
    </div>
  );
};

export default NotFound; 