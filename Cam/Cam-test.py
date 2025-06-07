import numpy as np
import cv2

def img_Correction(path):
  # 加载校准参数
  mtx = np.load('camera_matrix.npy')
  dist = np.load('distortion_coefficients.npy')

  # 图像校正部分
  img = cv2.imread(path)
  h, w = img.shape[:2]

  newcameramtx, roi = cv2.getOptimalNewCameraMatrix(mtx, dist, (w,h), 1, (w,h))
  dst = cv2.undistort(img, mtx, dist, None, newcameramtx)

  x, y, w, h = roi
  dst = dst[y:y+h, x:x+w]
  cv2.imwrite('C_' + path, dst)

def read_params():
  # 加载标定结果
  mtx = np.load('camera_matrix.npy')
  dist = np.load('distortion_coefficients.npy')
  
  # 安全提取参数
  dist_coeffs = dist.flatten()  # 确保1D数组
  required_coeffs = 5  # OpenCV标准畸变系数数量

  if len(dist_coeffs) < required_coeffs:
    print("参数不完整！注意检查标定质量")
    # 补零处理不完整参数
    dist_coeffs = np.pad(dist_coeffs, (0, required_coeffs-len(dist_coeffs)))
    k1, k2 = dist_coeffs[0], dist_coeffs[1]     # 径向畸变系数
    p1, p2 = dist_coeffs[2], dist_coeffs[3]     # 切向畸变系数

  # 提取内参
  fx, fy = mtx[0,0], mtx[1,1]  # 焦距
  cx, cy = mtx[0,2], mtx[1,2]  # 主点
  # k1, k2 = dist[0], dist[1]     # 径向畸变系数
  # p1, p2 = dist[2], dist[3]     # 切向畸变系数

  print(f"焦距(fx,fy): {fx:.2f}mm, {fy:.2f}mm")
  print(f"主点(cx,cy): {cx:.2f}/320, {cy:.2f}/240")
  print(dist)
  # print(f"畸变系数(k1,k2,p1,p2): {k1:.6f}, {k2:.6f}, {p1:.6f}, {p2:.6f}")

read_params()
img_Correction("test(2).jpg")
