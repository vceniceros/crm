import { Injectable } from '@angular/core';
import { BehaviorSubject, map, of, shareReplay } from 'rxjs';

import { MockUserProfile, MockUsersData } from '../models/user-profile.model';
import usersData from '../../../mocks/users-data.json';

const mockUsers = (usersData as MockUsersData).users;
const defaultUser = mockUsers[0];

@Injectable({ providedIn: 'root' })
export class MockUserContextService {
  private readonly activeUserIdSubject = new BehaviorSubject<number | string>(defaultUser.id);

  readonly users$ = of<MockUserProfile[]>(mockUsers).pipe(
    shareReplay({ bufferSize: 1, refCount: false })
  );
  readonly activeUserId$ = this.activeUserIdSubject.asObservable();
  readonly activeUser$ = this.activeUserId$.pipe(
    map((activeUserId) => mockUsers.find((user) => user.id === activeUserId) ?? defaultUser),
    shareReplay({ bufferSize: 1, refCount: true })
  );

  getUsers() {
    return this.users$;
  }

  activeUser() {
    return this.activeUser$;
  }

  getActiveUserSnapshot(): MockUserProfile {
    return mockUsers.find((user) => user.id === this.activeUserIdSubject.value) ?? defaultUser;
  }

  setActiveUser(userId: number | string): void {
    const userExists = mockUsers.some((user) => user.id === userId);

    if (!userExists) {
      return;
    }

    this.activeUserIdSubject.next(userId);
  }
}

export type { MockUserProfile };