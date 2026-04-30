// include/RobotModel.h
#ifndef ROBOTMODEL_H
#define ROBOTMODEL_H

#include <QString>
#include <QVector>
#include <TopoDS_Shape.hxx>
#include <AIS_Shape.hxx>
#include <AIS_Trihedron.hxx>
#include <Geom_Axis2Placement.hxx>
#include <gp_Trsf.hxx>
#include <gp_Pnt.hxx>
#include <gp_Dir.hxx>
#include <AIS_InteractiveContext.hxx>
#include <vector>
#include <array>

struct JointParam {
    int    axis;
    gp_Pnt pivot;
    gp_Dir rot_axis;
    double limit_min;
    double limit_max;
    double max_speed_deg_s;   // ← NEW: per-joint velocity limit from JSON
    QString geometryFile;
};

// ---------------------------------------------------------------
//  Jacobian-based IK solver result
// ---------------------------------------------------------------
struct IKResult {
    bool           success;
    QVector<double> angles;
    double         posError_mm;
    double         rotError_rad;
};

class RobotModel {
public:
    explicit RobotModel(const QString& jsonFilePath);

    bool checkSelfCollision();
    bool loadGeometry(const QString& robotsDir, const Handle(AIS_InteractiveContext)& context);
    void setJointAngles(const QVector<double>& angles, const Handle(AIS_InteractiveContext)& context);

    // Accessors
    QVector<Handle(AIS_Shape)>  getLinks()       const { return m_links; }
    Handle(AIS_Shape)           getBase()        const { return m_baseLink; }
    const QVector<JointParam>&  getJointParams() const { return m_joints; }
    gp_Trsf                     getTcpTransform()const { return m_tcpTransform; }

    // ---------------------------------------------------------------
    //  Forward kinematics (headless, no display update)
    // ---------------------------------------------------------------
    gp_Trsf computeHeadlessFK(const QVector<double>& angles) const;

    // ---------------------------------------------------------------
    //  Legacy IK interface (kept for backwards compatibility)
    // ---------------------------------------------------------------
    bool solveIK(double tx, double ty, double tz,
                 double trx, double try_, double trz,
                 QVector<double>& angles);

    // ---------------------------------------------------------------
    //  NEW: Velocity-aware Jacobian IK — solves for one time-step dt.
    //
    //  desiredLinearVel_mms  : target EE speed mm/s
    //  targetPos             : world target position (mm)
    //  targetRot             : world target rotation (quaternion)
    //  currentAngles [in/out]: updated in-place by at most one dt step
    //  dt_sec                : time-step duration (seconds)
    //
    //  Returns true when within tolerance.
    // ---------------------------------------------------------------
    // Returns true when converged.
    // actualDistMoved_mm (optional out): how far the TCP actually moved this step.
    bool stepIK(const gp_Pnt&        targetPos,
                const gp_Quaternion& targetRot,
                double               desiredLinearVel_mms,
                double               dt_sec,
                QVector<double>&     currentAngles,
                double*              actualDistMoved_mm = nullptr);

    // ---------------------------------------------------------------
    //  NEW: Compute the Cartesian Jacobian J (6×6) at given angles.
    //  Rows 0-2: translational (mm/rad), rows 3-5: rotational (rad/rad).
    // ---------------------------------------------------------------
    void computeJacobian(const QVector<double>& angles,
                         double J[6][6]) const;

    // ---------------------------------------------------------------
    //  NEW: Given a desired Cartesian velocity twist (vx,vy,vz,wx,wy,wz)
    //  compute joint velocities [deg/s] clamped to per-joint limits.
    //  Uses damped least-squares pseudoinverse.
    // ---------------------------------------------------------------
    bool cartesianVelToJointVel(const double twist[6],
                                const QVector<double>& currentAngles,
                                double jointVel_degPerSec[6]) const;

    void clearTrace(const Handle(AIS_InteractiveContext)& context);

private:
    QString             m_baseGeometryFile;
    QVector<JointParam> m_joints;

    Handle(AIS_Shape)              m_baseLink;
    QVector<Handle(AIS_Shape)>     m_links;
    Handle(AIS_Trihedron)          m_tcpMarker;
    gp_Trsf                        m_tcpTransform;

    std::vector<gp_Pnt>            m_tcpTrace;
    Handle(AIS_Shape)              m_traceShape;
};

#endif // ROBOTMODEL_H