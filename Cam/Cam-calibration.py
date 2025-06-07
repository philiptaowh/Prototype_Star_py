import os
import numpy as np
import cv2
import glob

# 相机标定部分
# 准备对象点
objp = np.zeros((7*7,3), np.float32)
objp[:,:2] = np.mgrid[0:7, 0:7].T.reshape(-1,2)

# 存储所有图像的对象的点，图像的点
objpoints = [] # 3d点
imgpoints = [] # 2d点

# 定义角点优化标准
criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.001)

# 读取图片
images = glob.glob(r'pic/*.jpg')
if not images:
    raise FileNotFoundError("未找到任何JPG文件，请检查pic/目录")
else:
    print(f"找到{len(images)}张标定图片")

for fname in images:
    img = cv2.imread(fname)
    if img is None:
        print(f"警告：无法读取{fname}")
        continue

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    ret, corners = cv2.findChessboardCorners(gray, (7,7), None)
    print(f"图片{fname} 角点检测: {'成功' if ret else '失败'}")
    
    if ret == True:
        objpoints.append(objp)
        corners2 = cv2.cornerSubPix(gray,corners, (11,11), (-1,-1), criteria)
        imgpoints.append(corners2)

        # 绘制并显示角点
        cv2.drawChessboardCorners(img, (7,7), corners2, ret)
        cv2.imshow('img', img)
        cv2.imwrite("calibration/" + os.path.basename(fname), img)
        cv2.waitKey(500)

# 执行相机标定
ret, mtx, dist, rvecs, tvecs = cv2.calibrateCamera(objpoints, imgpoints, gray.shape[::-1], None, None)

# 保存标定结果
np.save('camera_matrix.npy', mtx)
np.save('distortion_coefficients.npy', dist)