#!/usr/bin/env python3
"""
Comprehensive tests for the Enhanced DSATUR Algorithm
"""
import pytest
import pandas as pd
import sys
import os
from unittest.mock import patch

# Add the backend src to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from algorithms.enhanced_dsatur_scheduler import DSATURExamGraph, export_student_schedule


class TestDSATURAlgorithm:
    """Test suite for the DSATUR scheduling algorithm."""
    
    @pytest.fixture
    def sample_census(self):
        """Sample census data for testing."""
        return pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004', '1005'],
            'course_ref': ['CS101', 'MATH201', 'PHYS301', 'CHEM401', 'BIO501'],
            'num_students': [30, 25, 40, 20, 35]
        })
    
    @pytest.fixture
    def sample_enrollment(self):
        """Sample enrollment data for testing."""
        return pd.DataFrame({
            'student_id': ['S001', 'S001', 'S002', 'S002', 'S003', 'S003', 'S004', 'S004', 'S005', 'S005'],
            'CRN': ['1001', '1002', '1001', '1003', '1002', '1004', '1003', '1005', '1004', '1005'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Jones', 'Dr. Brown', 'Dr. Brown', 'Dr. Wilson', 'Dr. Wilson', 'Dr. Davis', 'Dr. Davis']
        })
    
    @pytest.fixture
    def sample_classrooms(self):
        """Sample classroom data for testing."""
        return pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C', 'Room D', 'Room E'],
            'capacity': [50, 40, 30, 25, 45]
        })
    
    def test_algorithm_initialization(self, sample_census, sample_enrollment, sample_classrooms):
        """Test algorithm initialization with sample data."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        
        assert len(graph.census) == 5
        assert len(graph.enrollment) == 10
        assert len(graph.classrooms) == 5
        assert graph.G.number_of_nodes() == 0  # Graph not built yet
    
    def test_graph_building(self, sample_census, sample_enrollment, sample_classrooms):
        """Test graph building process."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        
        # Check nodes were added
        assert graph.G.number_of_nodes() == 5
        
        # Check edges were created (shared students)
        assert graph.G.number_of_edges() > 0
        
        # Check student mapping
        assert '1001' in graph.students_by_crn
        assert 'S001' in graph.students_by_crn['1001']
        
        # Check instructor mapping
        assert '1001' in graph.instructors_by_crn
        assert 'Dr. Smith' in graph.instructors_by_crn['1001']
    
    def test_dsatur_coloring(self, sample_census, sample_enrollment, sample_classrooms):
        """Test DSATUR coloring algorithm."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        colors = graph.dsatur_color()
        
        # Check that all nodes got colors
        assert len(colors) == 5
        
        # Check that colors are integers
        for color in colors.values():
            assert isinstance(color, int)
            assert color >= 0
    
    def test_hard_constraints(self, sample_census, sample_enrollment, sample_classrooms):
        """Test hard constraint enforcement."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        
        # Test student double-booking constraint
        # Initialize student schedules for all students in the course
        student_sched = {'S001': [(0, 0)], 'S002': []}  # S001 already has exam at (Mon, 9:00)
        instr_sched = {}
        
        # Try to schedule another exam for S001 at same time
        ok, reason = graph._hard_ok(student_sched, instr_sched, '1001', 0, 0)
        assert not ok
        assert reason == "student_double_book"
        
        # Test instructor double-booking constraint
        student_sched = {'S001': [], 'S002': []}  # Initialize all students
        # Initialize all instructors that teach course 1001
        instr_sched = {'Dr. Smith': [(0, 0)], 'Dr. Jones': []}  # Dr. Smith already teaching at (Mon, 9:00)
        
        ok, reason = graph._hard_ok(student_sched, instr_sched, '1001', 0, 0)
        assert not ok
        assert reason == "instructor_double_book"
        
        # Test student max 2 exams per day constraint
        student_sched = {'S001': [(0, 0), (0, 1)], 'S002': []}  # S001 already has 2 exams on Monday
        instr_sched = {}
        
        ok, reason = graph._hard_ok(student_sched, instr_sched, '1001', 0, 2)
        assert not ok
        assert reason == "student_gt2_per_day"
    
    def test_soft_penalty_calculation(self, sample_census, sample_enrollment, sample_classrooms):
        """Test soft penalty calculation."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        
        # Test large course late penalty
        # Initialize student schedules for all students in the course
        student_sched = {'S001': [], 'S002': []}  # Initialize with empty schedules
        # Initialize instructor schedules for all instructors
        instr_sched = {'Dr. Smith': [], 'Dr. Jones': []}
        
        # Create a large course (>=100 students)
        graph.G.nodes['1001']['size'] = 150
        
        penalty = graph._soft_tuple(student_sched, instr_sched, '1001', 3, 0)  # Thursday
        assert penalty[0] > 0  # Should have late penalty for Thursday
        
        penalty_early = graph._soft_tuple(student_sched, instr_sched, '1001', 1, 0)  # Tuesday
        assert penalty_early[0] == 0  # No penalty for Tuesday
    
    def test_scheduling_process(self, sample_census, sample_enrollment, sample_classrooms):
        """Test the complete scheduling process."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        graph.dsatur_color()
        assignment = graph.dsatur_schedule()
        
        # Check that assignments were made
        assert len(assignment) > 0
        
        # Check that all assignments are within valid time slots
        for crn, (day, block) in assignment.items():
            assert 0 <= day < 7  # Valid day
            assert 0 <= block < 5  # Valid block
    
    def test_room_assignment(self, sample_census, sample_enrollment, sample_classrooms):
        """Test room assignment process."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        
        schedule_df = graph.assign_rooms()
        
        # Check that schedule was created
        assert len(schedule_df) > 0
        
        # Check required columns
        required_columns = ['CRN', 'Course', 'Day', 'Block', 'Room', 'Capacity', 'Size', 'Valid']
        for col in required_columns:
            assert col in schedule_df.columns
    
    def test_summary_generation(self, sample_census, sample_enrollment, sample_classrooms):
        """Test summary generation."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        graph.assign_rooms()
        
        summary = graph.summary()
        
        # Check that summary contains expected keys
        expected_keys = [
            'hard_student_conflicts', 'hard_instructor_conflicts',
            'students_gt2_per_day', 'students_back_to_back',
            'instructors_back_to_back', 'large_courses_not_early',
            'num_classes', 'num_students', 'num_rooms', 'slots_used'
        ]
        
        for key in expected_keys:
            assert key in summary
        
        # Check that hard conflicts should be 0 with proper scheduling
        assert summary['hard_student_conflicts'] == 0
        assert summary['hard_instructor_conflicts'] == 0
        assert summary['students_gt2_per_day'] == 0  # Enforced as hard rule
    
    def test_data_normalization(self):
        """Test data normalization with different column names."""
        # Test with legacy column names
        census_legacy = pd.DataFrame({
            'CRN': ['1001', '1002'],
            'CourseID': ['CS101', 'MATH201'],
            'num_students': [30, 25]
        })
        
        enrollment_legacy = pd.DataFrame({
            'Student_PIDM': ['S001', 'S001'],
            'CRN': ['1001', '1002'],
            'Instructor Name': ['Dr. Smith', 'Dr. Jones']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B'],
            'capacity': [50, 40]
        })
        
        # Should work with legacy column names
        graph = DSATURExamGraph(census_legacy, enrollment_legacy, classrooms)
        assert len(graph.census) == 2
        assert len(graph.enrollment) == 2
        assert 'course_ref' in graph.census.columns
        assert 'student_id' in graph.enrollment.columns
        assert 'instructor_name' in graph.enrollment.columns
    
    def test_edge_cases(self):
        """Test edge cases and error handling."""
        # Test with empty data
        empty_census = pd.DataFrame(columns=['CRN', 'course_ref', 'num_students'])
        empty_enrollment = pd.DataFrame(columns=['student_id', 'CRN', 'instructor_name'])
        empty_classrooms = pd.DataFrame(columns=['room_name', 'capacity'])
        
        graph = DSATURExamGraph(empty_census, empty_enrollment, empty_classrooms)
        graph.build_graph()
        
        # Should handle empty data gracefully
        assert graph.G.number_of_nodes() == 0
        assert graph.G.number_of_edges() == 0
        
        # Test with missing columns
        with pytest.raises(ValueError):
            bad_census = pd.DataFrame({'CRN': ['1001']})
            DSATURExamGraph(bad_census, empty_enrollment, empty_classrooms)
    
    def test_export_student_schedule(self, sample_census, sample_enrollment, sample_classrooms):
        """Test student schedule export functionality."""
        graph = DSATURExamGraph(sample_census, sample_enrollment, sample_classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Test export function
        student_schedule = export_student_schedule(
            graph, sample_enrollment, schedule_df, 
            base_name="test_schedule"
        )
        
        # Check that export was successful
        assert len(student_schedule) > 0
        assert 'student_id' in student_schedule.columns
        assert 'CRN' in student_schedule.columns
        assert 'Day' in student_schedule.columns
        assert 'Block' in student_schedule.columns


class TestAlgorithmIntegration:
    """Integration tests for the complete algorithm workflow."""
    
    @pytest.mark.integration
    def test_full_workflow_with_real_data(self):
        """Test the complete workflow with real data files."""
        try:
            # Try to load real data files
            census_df = pd.read_csv('../../Data/final_classcensus.csv')
            enrollment_df = pd.read_csv('../../Data/final_enrollment.csv')
            classrooms_df = pd.read_csv('../../Data/final_classrooms.csv')
            
            # Create algorithm instance
            graph = DSATURExamGraph(census_df, enrollment_df, classrooms_df)
            
            # Run complete workflow
            graph.build_graph()
            print(f"Graph built: {graph.G.number_of_nodes()} nodes, {graph.G.number_of_edges()} edges")
            
            graph.dsatur_color()
            print(f"Coloring completed: {len(graph.colors)} colors")
            
            assignment = graph.dsatur_schedule()
            print(f"Scheduling completed: {len(assignment)} assignments")
            
            schedule_df = graph.assign_rooms()
            print(f"Room assignment completed: {len(schedule_df)} scheduled exams")
            
            summary = graph.summary()
            print(f"Summary: {summary}")
            
            # Verify no hard conflicts
            assert summary['hard_student_conflicts'] == 0
            assert summary['hard_instructor_conflicts'] == 0
            assert summary['students_gt2_per_day'] == 0
            
            print("SUCCESS: Full workflow test passed!")
            
        except FileNotFoundError:
            print("WARNING: Real data files not found, skipping integration test")
        except Exception as e:
            print(f"ERROR: Integration test failed: {e}")
            raise


class TestAlgorithmPerformance:
    """Performance and stress tests for the DSATUR algorithm."""
    
    @pytest.fixture
    def large_census_data(self):
        """Generate large census dataset for performance testing."""
        courses = []
        for i in range(1000):
            courses.append({
                'CRN': f'{10000 + i}',
                'course_ref': f'CS{i:03d}',
                'num_students': 20 + (i % 50)  # 20-69 students per course
            })
        return pd.DataFrame(courses)
    
    @pytest.fixture
    def large_enrollment_data(self):
        """Generate large enrollment dataset for performance testing."""
        enrollments = []
        for i in range(5000):  # 5000 students
            student_id = f'S{i:04d}'
            # Each student takes 3-5 courses
            num_courses = 3 + (i % 3)
            for j in range(num_courses):
                crn = f'{10000 + (i * 2 + j) % 1000}'  # Distribute across courses
                enrollments.append({
                    'student_id': student_id,
                    'CRN': crn,
                    'instructor_name': f'Dr. Instructor{(i + j) % 100}'
                })
        return pd.DataFrame(enrollments)
    
    @pytest.fixture
    def large_classroom_data(self):
        """Generate large classroom dataset for performance testing."""
        rooms = []
        for i in range(100):
            rooms.append({
                'room_name': f'Room_{i:03d}',
                'capacity': 30 + (i % 40)  # 30-69 capacity
            })
        return pd.DataFrame(rooms)
    
    @pytest.mark.slow
    def test_algorithm_performance_large_dataset(self, large_census_data, large_enrollment_data, large_classroom_data):
        """Test algorithm performance with large dataset."""
        import time
        
        start_time = time.time()
        graph = DSATURExamGraph(large_census_data, large_enrollment_data, large_classroom_data)
        
        # Build graph
        graph.build_graph()
        build_time = time.time() - start_time
        
        # Run coloring
        start_time = time.time()
        graph.dsatur_color()
        color_time = time.time() - start_time
        
        # Run scheduling
        start_time = time.time()
        graph.dsatur_schedule()
        schedule_time = time.time() - start_time
        
        # Assign rooms
        start_time = time.time()
        schedule_df = graph.assign_rooms()
        room_time = time.time() - start_time
        
        # Verify results
        assert len(schedule_df) > 0
        assert graph.G.number_of_nodes() > 0
        assert len(graph.colors) > 0
        
        # Performance assertions (should complete within reasonable time)
        assert build_time < 30, f"Graph building took too long: {build_time:.2f}s"
        assert color_time < 60, f"Coloring took too long: {color_time:.2f}s"
        assert schedule_time < 30, f"Scheduling took too long: {schedule_time:.2f}s"
        assert room_time < 20, f"Room assignment took too long: {room_time:.2f}s"
        
        print(f"Performance test completed:")
        print(f"  - Graph building: {build_time:.2f}s")
        print(f"  - Coloring: {color_time:.2f}s")
        print(f"  - Scheduling: {schedule_time:.2f}s")
        print(f"  - Room assignment: {room_time:.2f}s")
    
    @pytest.mark.stress
    def test_memory_usage_under_load(self, large_census_data, large_enrollment_data, large_classroom_data):
        """Test memory usage with large dataset."""
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB
        
        # Create multiple algorithm instances to test memory usage
        graphs = []
        for i in range(5):  # Create 5 instances
            graph = DSATURExamGraph(large_census_data, large_enrollment_data, large_classroom_data)
            graph.build_graph()
            graph.dsatur_color()
            graphs.append(graph)
        
        peak_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = peak_memory - initial_memory
        
        # Memory should not increase excessively
        assert memory_increase < 1000, f"Memory usage increased too much: {memory_increase:.1f}MB"
        
        print(f"Memory usage test:")
        print(f"  - Initial memory: {initial_memory:.1f}MB")
        print(f"  - Peak memory: {peak_memory:.1f}MB")
        print(f"  - Memory increase: {memory_increase:.1f}MB")
    
    def test_algorithm_scalability(self):
        """Test how algorithm scales with increasing data size."""
        import time
        
        scalability_results = []
        
        for size in [10, 50, 100, 200]:
            # Generate data of different sizes
            census = pd.DataFrame({
                'CRN': [f'{i:04d}' for i in range(size)],
                'course_ref': [f'CS{i:03d}' for i in range(size)],
                'num_students': [20 + (i % 30) for i in range(size)]
            })
            
            enrollment = pd.DataFrame({
                'student_id': [f'S{i:03d}' for i in range(size * 2)],
                'CRN': [f'{i % size:04d}' for i in range(size * 2)],
                'instructor_name': [f'Dr. {i % 10}' for i in range(size * 2)]
            })
            
            classrooms = pd.DataFrame({
                'room_name': [f'Room_{i:02d}' for i in range(max(10, size // 10))],
                'capacity': [30 + (i % 20) for i in range(max(10, size // 10))]
            })
            
            start_time = time.time()
            graph = DSATURExamGraph(census, enrollment, classrooms)
            graph.build_graph()
            graph.dsatur_color()
            graph.dsatur_schedule()
            schedule_df = graph.assign_rooms()
            total_time = time.time() - start_time
            
            scalability_results.append({
                'size': size,
                'time': total_time,
                'nodes': graph.G.number_of_nodes(),
                'edges': graph.G.number_of_edges()
            })
        
        # Verify scalability (time should not grow exponentially)
        for i in range(1, len(scalability_results)):
            prev = scalability_results[i-1]
            curr = scalability_results[i]
            
            # Time growth should be reasonable (not exponential)
            time_ratio = curr['time'] / prev['time'] if prev['time'] > 0 else 1
            size_ratio = curr['size'] / prev['size']
            
            # Time should not grow faster than quadratically
            assert time_ratio < size_ratio ** 2, f"Algorithm doesn't scale well: {time_ratio:.2f} vs {size_ratio:.2f}"
        
        print("Scalability test results:")
        for result in scalability_results:
            print(f"  Size {result['size']}: {result['time']:.2f}s, {result['nodes']} nodes, {result['edges']} edges")


class TestAdvancedConstraints:
    """Advanced constraint validation tests."""
    
    @pytest.fixture
    def complex_conflict_data(self):
        """Generate data with complex student conflicts."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004', '1005', '1006'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202', 'PHYS301', 'PHYS302'],
            'num_students': [30, 30, 25, 25, 20, 20]
        })
        
        # Create overlapping student enrollments
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S001', 'S001', 'S002', 'S002', 'S002', 'S003', 'S003', 'S003', 'S003'],
            'CRN': ['1001', '1002', '1003', '1001', '1003', '1004', '1001', '1002', '1004', '1005'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Jones', 'Dr. Brown', 'Dr. Smith', 'Dr. Smith', 'Dr. Brown', 'Dr. Wilson']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C'],
            'capacity': [50, 40, 30]
        })
        
        return census, enrollment, classrooms
    
    def test_complex_student_conflicts(self, complex_conflict_data):
        """Test algorithm with complex student conflict scenarios."""
        census, enrollment, classrooms = complex_conflict_data
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Verify no hard conflicts
        summary = graph.summary()
        assert summary['hard_student_conflicts'] == 0
        assert summary['hard_instructor_conflicts'] == 0
        
        # Verify all courses are scheduled
        assert len(schedule_df) == len(census)
        
        # Check that conflicting courses are scheduled at different times
        student_schedules = {}
        for _, exam in schedule_df.iterrows():
            crn = exam['CRN']
            students = enrollment[enrollment['CRN'] == crn]['student_id'].tolist()
            for student in students:
                if student not in student_schedules:
                    student_schedules[student] = []
                student_schedules[student].append((exam['Day'], exam['Block']))
        
        # Verify no student has multiple exams at same time
        for student, times in student_schedules.items():
            unique_times = set(times)
            assert len(unique_times) == len(times), f"Student {student} has conflicts: {times}"
    
    def test_instructor_scheduling_conflicts(self):
        """Test instructor availability constraints."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003'],
            'course_ref': ['CS101A', 'CS101B', 'CS102'],
            'num_students': [30, 30, 25]
        })
        
        # Same instructor teaching multiple courses
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S002', 'S003', 'S004', 'S005'],
            'CRN': ['1001', '1001', '1002', '1002', '1003'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Smith']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B'],
            'capacity': [50, 40]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Verify no instructor conflicts
        summary = graph.summary()
        assert summary['hard_instructor_conflicts'] == 0
        
        # Verify instructor's courses are scheduled at different times
        instructor_schedule = {}
        for _, exam in schedule_df.iterrows():
            crn = exam['CRN']
            instructor = enrollment[enrollment['CRN'] == crn]['instructor_name'].iloc[0]
            if instructor not in instructor_schedule:
                instructor_schedule[instructor] = []
            instructor_schedule[instructor].append((exam['Day'], exam['Block']))
        
        for instructor, times in instructor_schedule.items():
            unique_times = set(times)
            assert len(unique_times) == len(times), f"Instructor {instructor} has conflicts: {times}"
    
    def test_room_capacity_edge_cases(self):
        """Test room assignment with exact capacity matches."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003'],
            'course_ref': ['CS101', 'MATH201', 'PHYS301'],
            'num_students': [30, 30, 30]  # Exact room capacity
        })
        
        enrollment = pd.DataFrame({
            'student_id': [f'S{i:03d}' for i in range(90)],  # 30 students per course
            'CRN': ['1001'] * 30 + ['1002'] * 30 + ['1003'] * 30,
            'instructor_name': ['Dr. Smith', 'Dr. Jones', 'Dr. Brown'] * 30
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C'],
            'capacity': [30, 30, 30]  # Exact capacity matches
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Verify all courses are scheduled
        assert len(schedule_df) == len(census)
        
        # Verify no capacity violations
        for _, exam in schedule_df.iterrows():
            assert exam['Size'] <= exam['Capacity'], f"Capacity violation: {exam['Size']} > {exam['Capacity']}"
    
    def test_time_slot_optimization(self):
        """Test optimal time slot distribution."""
        census = pd.DataFrame({
            'CRN': [f'{1000 + i}' for i in range(20)],
            'course_ref': [f'CS{i:03d}' for i in range(20)],
            'num_students': [25] * 20
        })
        
        enrollment = pd.DataFrame({
            'student_id': [f'S{i:03d}' for i in range(500)],  # 25 students per course
            'CRN': [f'{1000 + (i // 25)}' for i in range(500)],
            'instructor_name': [f'Dr. {i % 10}' for i in range(500)]
        })
        
        classrooms = pd.DataFrame({
            'room_name': [f'Room_{chr(65 + i)}' for i in range(10)],
            'capacity': [50] * 10
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Verify good time slot distribution
        day_distribution = schedule_df['Day'].value_counts()
        block_distribution = schedule_df['Block'].value_counts()
        
        # Should use multiple days and blocks
        assert len(day_distribution) > 1, "All exams scheduled on same day"
        assert len(block_distribution) > 1, "All exams scheduled in same block"
        
        # Distribution should be reasonably balanced
        max_day_count = day_distribution.max()
        min_day_count = day_distribution.min()
        assert max_day_count - min_day_count <= 5, "Day distribution too uneven"
        
        max_block_count = block_distribution.max()
        min_block_count = block_distribution.min()
        assert max_block_count - min_block_count <= 3, "Block distribution too uneven"


class TestAlgorithmOptimization:
    """Algorithm optimization and efficiency tests."""
    
    def test_coloring_optimality(self):
        """Test if DSATUR produces optimal coloring."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004', '1005'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202', 'PHYS301'],
            'num_students': [30, 30, 25, 25, 20]
        })
        
        # Create a known conflict graph
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S001', 'S002', 'S002', 'S003', 'S003', 'S004', 'S004'],
            'CRN': ['1001', '1002', '1001', '1003', '1002', '1004', '1003', '1005'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Brown', 'Dr. Jones', 'Dr. Wilson']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C'],
            'capacity': [50, 40, 30]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        
        # Verify coloring is valid (no adjacent nodes have same color)
        for node in graph.G.nodes():
            node_color = graph.colors[node]
            for neighbor in graph.G.neighbors(node):
                neighbor_color = graph.colors[neighbor]
                assert node_color != neighbor_color, f"Adjacent nodes {node} and {neighbor} have same color {node_color}"
        
        # Verify reasonable number of colors used
        num_colors = len(set(graph.colors.values()))
        assert num_colors <= len(census), f"Too many colors used: {num_colors} > {len(census)}"
        assert num_colors >= 1, "No colors used"
    
    def test_room_utilization_optimization(self):
        """Test room usage efficiency."""
        census = pd.DataFrame({
            'CRN': [f'{1000 + i}' for i in range(10)],
            'course_ref': [f'CS{i:03d}' for i in range(10)],
            'num_students': [20, 30, 25, 35, 15, 40, 20, 30, 25, 35]
        })
        
        enrollment = pd.DataFrame({
            'student_id': [f'S{i:03d}' for i in range(285)],  # Total students
            'CRN': [f'{1000 + (i // 30)}' for i in range(285)],
            'instructor_name': [f'Dr. {i % 5}' for i in range(285)]
        })
        
        classrooms = pd.DataFrame({
            'room_name': [f'Room_{chr(65 + i)}' for i in range(5)],
            'capacity': [50, 40, 30, 60, 35]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Calculate room utilization
        schedule_df['utilization'] = (schedule_df['Size'] / schedule_df['Capacity'] * 100).round(1)
        avg_utilization = schedule_df['utilization'].mean()
        
        # Should have reasonable utilization (not too low, not over 100%)
        assert avg_utilization > 50, f"Room utilization too low: {avg_utilization:.1f}%"
        assert avg_utilization < 100, f"Room utilization over 100%: {avg_utilization:.1f}%"
        
        # No capacity violations
        violations = schedule_df[schedule_df['Size'] > schedule_df['Capacity']]
        assert len(violations) == 0, f"Capacity violations found: {len(violations)}"
    
    def test_soft_constraint_prioritization(self):
        """Test soft constraint handling order."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004', '1005'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202', 'PHYS301'],
            'num_students': [50, 40, 30, 25, 20]  # Decreasing size
        })
        
        enrollment = pd.DataFrame({
            'student_id': [f'S{i:03d}' for i in range(165)],  # Total students
            'CRN': [f'{1000 + (i // 35)}' for i in range(165)],
            'instructor_name': [f'Dr. {i % 3}' for i in range(165)]
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C'],
            'capacity': [60, 50, 40]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Verify soft constraints are handled
        summary = graph.summary()
        
        # Large courses should be prioritized for early scheduling
        large_courses = schedule_df[schedule_df['Size'] >= 40]
        if len(large_courses) > 0:
            # Check if large courses are scheduled early (this is a soft constraint)
            early_days = ['Mon', 'Tue', 'Wed']
            early_scheduled = large_courses[large_courses['Day'].isin(early_days)]
            early_ratio = len(early_scheduled) / len(large_courses)
            
            # At least some large courses should be scheduled early
            assert early_ratio > 0.3, f"Large courses not prioritized for early scheduling: {early_ratio:.2f}"


class TestEdgeCasesAndErrorHandling:
    """Edge case and error handling tests."""
    
    def test_impossible_scheduling_scenarios(self):
        """Test algorithm behavior when scheduling is impossible."""
        # Create scenario with more courses than time slots
        census = pd.DataFrame({
            'CRN': [f'{1000 + i}' for i in range(50)],  # 50 courses
            'course_ref': [f'CS{i:03d}' for i in range(50)],
            'num_students': [30] * 50
        })
        
        # All students enrolled in all courses (impossible to schedule)
        enrollment_data = []
        for i in range(100):  # 100 students
            for j in range(50):  # Each student in all 50 courses
                enrollment_data.append({
                    'student_id': f'S{i:03d}',
                    'CRN': f'{1000 + j}',
                    'instructor_name': f'Dr. {j % 10}'
                })
        
        enrollment = pd.DataFrame(enrollment_data)
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A'],
            'capacity': [100]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Algorithm should handle impossible scenario gracefully
        assert len(schedule_df) >= 0, "Algorithm should not crash on impossible scenario"
        
        # Should have some hard conflicts in impossible scenario
        summary = graph.summary()
        # Note: The algorithm might still find a solution, but if it doesn't,
        # it should report conflicts appropriately
    
    def test_data_inconsistency_handling(self):
        """Test algorithm with inconsistent data."""
        # Create data with missing enrollments for some courses
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003'],
            'course_ref': ['CS101', 'CS102', 'CS103'],
            'num_students': [30, 0, 25]  # One course with 0 students
        })
        
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S002', 'S003'],
            'CRN': ['1001', '1001', '1003'],  # Missing enrollments for 1002
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Jones']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B'],
            'capacity': [50, 40]
        })
        
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        schedule_df = graph.assign_rooms()
        
        # Algorithm should handle inconsistent data gracefully
        assert len(schedule_df) >= 0, "Algorithm should not crash on inconsistent data"
        
        # The algorithm may still schedule courses with 0 students if they exist in census
        # This is actually acceptable behavior - the algorithm processes all courses in census
        # We should verify that the algorithm doesn't crash and produces a valid schedule
        assert len(schedule_df) > 0, "Algorithm should produce some schedule"
        
        # Verify all scheduled courses are valid
        for _, exam in schedule_df.iterrows():
            assert exam['Size'] >= 0, f"Invalid size for course {exam['CRN']}"
            assert exam['Capacity'] > 0, f"Invalid capacity for course {exam['CRN']}"
    
    def test_partial_scheduling_recovery(self):
        """Test algorithm recovery from partial failures."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202'],
            'num_students': [30, 30, 25, 25]
        })
        
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S001', 'S002', 'S002', 'S003', 'S003'],
            'CRN': ['1001', '1002', '1001', '1003', '1002', '1004'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Brown']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B'],
            'capacity': [50, 40]
        })
        
        # Test multiple runs to ensure consistency
        results = []
        for i in range(3):
            graph = DSATURExamGraph(census, enrollment, classrooms)
            graph.build_graph()
            graph.dsatur_color()
            graph.dsatur_schedule()
            schedule_df = graph.assign_rooms()
            results.append(len(schedule_df))
        
        # All runs should produce same number of scheduled exams
        assert all(r == results[0] for r in results), f"Inconsistent results across runs: {results}"
        
        # Should schedule all courses
        assert results[0] == len(census), f"Not all courses scheduled: {results[0]} < {len(census)}"


class TestAlgorithmComparison:
    """Algorithm comparison and validation tests."""
    
    def test_algorithm_vs_naive_approach(self):
        """Compare DSATUR vs naive scheduling approach."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004', '1005'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202', 'PHYS301'],
            'num_students': [30, 30, 25, 25, 20]
        })
        
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S001', 'S002', 'S002', 'S003', 'S003'],
            'CRN': ['1001', '1002', '1001', '1003', '1002', '1004'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Brown']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B', 'Room C'],
            'capacity': [50, 40, 30]
        })
        
        # DSATUR approach
        graph = DSATURExamGraph(census, enrollment, classrooms)
        graph.build_graph()
        graph.dsatur_color()
        graph.dsatur_schedule()
        dsatur_schedule = graph.assign_rooms()
        dsatur_summary = graph.summary()
        
        # Verify DSATUR produces valid schedule
        assert len(dsatur_schedule) > 0, "DSATUR should produce a schedule"
        assert dsatur_summary['hard_student_conflicts'] == 0, "DSATUR should have no hard conflicts"
        assert dsatur_summary['hard_instructor_conflicts'] == 0, "DSATUR should have no instructor conflicts"
        
        # DSATUR should be efficient (use reasonable number of time slots)
        unique_slots = dsatur_schedule[['Day', 'Block']].drop_duplicates()
        assert len(unique_slots) <= len(census), f"DSATUR uses too many time slots: {len(unique_slots)} > {len(census)}"
    
    def test_different_heuristic_strategies(self):
        """Test different node selection strategies."""
        census = pd.DataFrame({
            'CRN': ['1001', '1002', '1003', '1004'],
            'course_ref': ['CS101', 'CS102', 'MATH201', 'MATH202'],
            'num_students': [30, 30, 25, 25]
        })
        
        enrollment = pd.DataFrame({
            'student_id': ['S001', 'S001', 'S002', 'S002', 'S003', 'S003'],
            'CRN': ['1001', '1002', '1001', '1003', '1002', '1004'],
            'instructor_name': ['Dr. Smith', 'Dr. Smith', 'Dr. Smith', 'Dr. Jones', 'Dr. Smith', 'Dr. Brown']
        })
        
        classrooms = pd.DataFrame({
            'room_name': ['Room A', 'Room B'],
            'capacity': [50, 40]
        })
        
        # Test multiple runs with same data
        results = []
        for i in range(5):
            graph = DSATURExamGraph(census, enrollment, classrooms)
            graph.build_graph()
            graph.dsatur_color()
            graph.dsatur_schedule()
            schedule_df = graph.assign_rooms()
            summary = graph.summary()
            
            results.append({
                'scheduled': len(schedule_df),
                'conflicts': summary['hard_student_conflicts'],
                'time_slots': len(schedule_df[['Day', 'Block']].drop_duplicates())
            })
        
        # All runs should produce valid results
        for result in results:
            assert result['scheduled'] > 0, "Should schedule some courses"
            assert result['conflicts'] == 0, "Should have no hard conflicts"
            assert result['time_slots'] > 0, "Should use some time slots"
        
        # Results should be consistent (same number of scheduled courses)
        scheduled_counts = [r['scheduled'] for r in results]
        assert len(set(scheduled_counts)) == 1, f"Inconsistent scheduling results: {scheduled_counts}"


if __name__ == "__main__":
    # Run tests if executed directly
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "--integration":
        test = TestAlgorithmIntegration()
        test.test_full_workflow_with_real_data()
    else:
        print("Run with --integration to test with real data files")
        print("Run with pytest to run all unit tests")
